"""
LLM Inference Module for Video Analysis
"""

import json
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional, List, Tuple
import cv2
from PIL import Image
from transformers import AutoProcessor, Gemma3nForConditionalGeneration
import torch
import setproctitle


class LLMInferenceEngine:
    """Handles LLM inference for video analysis."""
    
    def __init__(self, prompt_file: str = "prompt.txt", config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM inference engine.
        
        Args:
            prompt_file: Path to the prompt file for LLM inference
            config: Optional configuration dictionary for LLM settings
        """
        self.prompt_file = prompt_file
        self.config = config or {}
        
        # Initialize LLM model (lazy loading)
        self.model = None
        self.processor = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _extract_frames(self, video_path: str, num_frames: int = 10) -> List[Tuple[Image.Image, float]]:
        """Extract frames from video file."""
        # Log file size before opening
        try:
            file_size = os.path.getsize(video_path)
            self.logger.info(f"Video file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        except Exception as e:
            self.logger.info(f"Video file size: N/A (error: {e})")

        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            self.logger.error("Could not open video file")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate step size to evenly distribute frames
        step = max(1, total_frames // num_frames)
        frames = []
        
        for i in range(num_frames):
            frame_idx = i * step
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            timestamp = round(frame_idx / fps, 2)
            frames.append((img, timestamp))
        
        cap.release()
        return frames
    
    def _initialize_model(self):
        """Initialize the LLM model (lazy loading)."""
        if self.model is None:
            # Set process name for nvidia-smi display
            setproctitle.setproctitle("sunny-osprey")
            self.logger.info("Initializing LLM model...")
            
            # Get model name from config or use default
            model_name = self.config.get('model_name', 'gemma-3n-E2B-it')
            model_id = f"google/{model_name}"
            
            # Prepare model initialization parameters
            model_kwargs = {
                'torch_dtype': torch.bfloat16,
            }
            
            # Create custom device map to keep audio tower on CPU
            if torch.cuda.is_available():
                # Load model temporarily to get module names
                temp_model = Gemma3nForConditionalGeneration.from_pretrained(
                    model_id, 
                    torch_dtype=torch.bfloat16,
                    device_map="cpu"  # Load on CPU first to inspect
                )
                
                # Create comprehensive device map
                device_map = {}
                
                for name, _ in temp_model.named_modules():
                    if 'audio_tower' in name or 'embed_audio' in name:
                        device_map[name] = "cpu"
                    else:
                        device_map[name] = 0  # GPU device 0
                
                # Clean up temp model
                del temp_model
                torch.cuda.empty_cache()
                
                model_kwargs['device_map'] = device_map
                self.logger.info("Using custom device map: audio components on CPU, rest on GPU")
            else:
                # CPU-only mode
                model_kwargs['device_map'] = "cpu"
                self.logger.info("CUDA not available, using CPU-only mode")
            
            # Add attention implementation
            attn_implementation = self.config.get('attn_implementation', 'eager')
            if attn_implementation:
                # Check if flash_attention_2 is available, fall back to eager if not
                if attn_implementation == 'flash_attention_2':
                    try:
                        import flash_attn
                        model_kwargs['attn_implementation'] = attn_implementation
                        self.logger.info("Using Flash Attention 2 for optimized GPU memory usage")
                    except ImportError:
                        self.logger.warning("Flash Attention 2 not available, falling back to eager")
                        model_kwargs['attn_implementation'] = 'eager'
                else:
                    model_kwargs['attn_implementation'] = attn_implementation
            
            # Only add max_memory if specified in config
            if 'max_memory' in self.config:
                model_kwargs['max_memory'] = self.config['max_memory']
                self.logger.info(f"Using max_memory from config: {self.config['max_memory']}")
            else:
                self.logger.info("No max_memory specified in config, using default device mapping")
            
            # Use custom device map for optimal GPU memory usage
            self.model = Gemma3nForConditionalGeneration.from_pretrained(
                model_id, 
                **model_kwargs
            ).eval()
            
            self.processor = AutoProcessor.from_pretrained(model_id)
            self.logger.info(f"LLM model initialized with device mapping: auto")
            
            # Print device and size information for model parameters (sorted by size)
            self.logger.info("Model parameter devices and sizes (sorted by size, largest first):")
            self.logger.info(f"{'Parameter Name':<60} {'Device':<6} {'Memory(MB)':>10} {'Params(M)':>9} {'Shape'}")
            self.logger.info("-" * 95)
            total_params = 0
            param_info = []
            gpu_memory = 0
            cpu_memory = 0
            
            for name, param in self.model.named_parameters():
                param_size = param.numel() * param.element_size()
                param_size_mb = param_size / (1024 * 1024)
                param_count = param.numel()
                total_params += param_count
                param_info.append((name, param.device, param_size_mb, param_count, list(param.shape)))
                
                # Track memory by device
                if param.device.type == 'cuda':
                    gpu_memory += param_size_mb
                else:
                    cpu_memory += param_size_mb
            
            # Sort by size (largest first)
            param_info.sort(key=lambda x: x[2], reverse=True)
            
            for name, device, size_mb, param_count, shape in param_info:
                param_count_m = param_count / 1_000_000
                device_str = str(device)
                self.logger.info(f"{name:<60} {device_str:<6} {size_mb:>8.1f}MB {param_count_m:>7.1f}M {shape}")
            
            total_params_m = total_params / 1_000_000
            total_memory = gpu_memory + cpu_memory
            self.logger.info(f"Total parameters: {total_params_m:.2f}M (GPU: {gpu_memory:.2f} MB, CPU: {cpu_memory:.2f} MB, Total: {total_memory:.2f} MB)")
    
    def run_inference(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Run LLM inference on video frames."""
        try:
            # Initialize model if needed
            self._initialize_model()
            
            # Extract frames
            video_frames = self._extract_frames(video_path, num_frames=10)
            if not video_frames:
                self.logger.error("No frames extracted from video")
                return None
            
            # Read prompt
            with open(self.prompt_file, "r") as f:
                user_prompt = f.read()
            
            # Read system prompt from system_prompt.txt in working directory
            try:
                with open('system_prompt.txt', 'r') as sysf:
                    system_prompt = sysf.read().strip()
            except Exception as e:
                self.logger.error(f"Could not read system_prompt.txt: {e}")
                system_prompt = "You are a helpful security camera video analysis assistant."
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}]
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}]
                }
            ]
            
            # Add frames to messages
            frames_dir = tempfile.mkdtemp(prefix="frames_")
            try:
                for img, timestamp in video_frames:
                    frame_path = os.path.join(frames_dir, f"frame_{timestamp}.png")
                    img.save(frame_path)
                    messages[1]["content"].append({"type": "image", "url": frame_path})
                
                # Process with model
                inputs = self.processor.apply_chat_template(
                    messages, add_generation_prompt=True, tokenize=True,
                    return_dict=True, return_tensors="pt"
                )
                # Move to appropriate device (GPU if available, otherwise CPU)
                device = next(self.model.parameters()).device
                inputs = {k: v.to(device) for k, v in inputs.items()}
                
                input_length = inputs["input_ids"].shape[-1]
                
                # Generate response
                start_time = time.perf_counter()
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=500,
                    do_sample=False
                )
                output = output[0][input_length:]
                response = self.processor.decode(output, skip_special_tokens=True)
                end_time = time.perf_counter()
                
                self.logger.info(f"LLM inference completed in {end_time - start_time:.2f} seconds")
                
                # Parse JSON response
                try:
                    # Extract JSON from response (in case there's extra text)
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start != -1 and json_end != 0:
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        return result
                    else:
                        self.logger.error("No JSON found in LLM response")
                        return {"error": "No JSON found in response", "raw_response": response}
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    return {"error": "Invalid JSON response", "raw_response": response}
                    
            finally:
                # Clean up frames directory
                import shutil
                shutil.rmtree(frames_dir, ignore_errors=True)
                
        except Exception as e:
            import traceback
            self.logger.error(f"Error running LLM inference: {e}")
            self.logger.error("Traceback:\n" + traceback.format_exc())
            return {"error": str(e)} 