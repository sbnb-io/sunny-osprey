import os
import json
import logging
import requests
from typing import Dict, Any
from datetime import datetime, timezone

class GrafanaIRMAlert:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.url = self.config.get('url', '')
        self.api_key = self.config.get('api_key', '')
        self.logger = logging.getLogger(__name__)
        self.enabled = self._validate_config()

    def _validate_config(self):
        if not self.url or not self.api_key:
            self.logger.warning("Missing required Grafana configuration: url or api_key")
            self.logger.warning("Grafana alerts will be disabled")
            return False
        return True

    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _prepare_grafana_payload(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        # Use incident_data fields
        llm_description = incident_data['description']
        if len(llm_description) > 100:
            llm_description = llm_description[:97] + "..."
        
        is_suspicious = incident_data.get('is_suspicious', False)
        if is_suspicious:
            enhanced_title = f"Security Alert: {llm_description} - Event {incident_data['event_id']}"
            severity = 'critical'
            room_prefix = 'security-alert'
        else:
            enhanced_title = f"NORMAL ACTIVITY: {llm_description} - Event {incident_data['event_id']}"
            severity = 'info'
            room_prefix = 'normal-activity'
        
        payload = {
            'title': enhanced_title,
            'description': incident_data['description'],
            'severity': severity,
            'status': 'active',
            'isDrill': False,
            'roomPrefix': room_prefix,
            'attachCaption': incident_data['description'],
            'attachURL': incident_data['video_url']
        }
        return payload

    def _create_irm_incident(self, payload: Dict[str, Any]) -> bool:
        try:
            # Construct the full URL for creating incidents
            incident_url = f"{self.url}/api/plugins/grafana-irm-app/resources/api/v1/IncidentsService.CreateIncident"
            headers = self._get_auth_headers()
            response = requests.post(incident_url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                incident_id = response.json().get('id', 'unknown')
                self.logger.info(f"Incident created in Grafana IRM successfully with ID: {incident_id}")
                return True
            else:
                self.logger.warning(f"Failed to create incident: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error creating IRM incident: {e}")
            return False

    def send_incident(self, incident_data: Dict[str, Any]) -> bool:
        if not self.enabled:
            self.logger.warning("Grafana IRM incidents are disabled due to missing configuration")
            return False
        try:
            is_suspicious = incident_data.get('is_suspicious', False)
            event_id = incident_data.get('event_id')
            
            if is_suspicious:
                self.logger.info(f"Suspicious activity detected for event {event_id}, sending Grafana IRM alert")
            else:
                self.logger.info(f"Normal activity detected for event {event_id}, sending Grafana IRM notification")
            
            payload = self._prepare_grafana_payload(incident_data)
            return self._create_irm_incident(payload)
        except Exception as e:
            self.logger.error(f"Error sending Grafana IRM incident for event {incident_data.get('event_id')}: {e}")
            return False 