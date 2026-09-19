import re
import json
import logging
import httpx
from typing import List, Dict, Any
from backend.schemas import MitreTechnique

logger = logging.getLogger(__name__)

ATTACK_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

DEFAULT_TECHNIQUES = [
    MitreTechnique(technique_id="T1566.001", name="Spearphishing Attachment", tactic="Initial Access", description="Spearphishing with malicious attachment", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1059.001", name="PowerShell", tactic="Execution", description="Execution of commands using PowerShell", platforms=["Windows"]),
    MitreTechnique(technique_id="T1003.001", name="LSASS Memory", tactic="Credential Access", description="Dumping LSASS process memory to extract credentials", platforms=["Windows"]),
    MitreTechnique(technique_id="T1021.002", name="SMB/Windows Admin Shares", tactic="Lateral Movement", description="Lateral movement via SMB administrative shares", platforms=["Windows"]),
    MitreTechnique(technique_id="T1082", name="System Information Discovery", tactic="Discovery", description="Gathering detailed system info", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1083", name="File and Directory Discovery", tactic="Discovery", description="Listing files and directories", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1005", name="Data from Local System", tactic="Collection", description="Collecting sensitive files locally", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1048", name="Exfiltration Over Alternative Protocol", tactic="Exfiltration", description="Exfiltrating data using non-standard network protocols", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1547.001", name="Registry Run Keys / Startup Folder", tactic="Persistence", description="Achieving persistence via registry run keys", platforms=["Windows"]),
    MitreTechnique(technique_id="T1053.005", name="Scheduled Task", tactic="Persistence", description="Scheduled task creation for persistence", platforms=["Windows"]),
    MitreTechnique(technique_id="T1055", name="Process Injection", tactic="Privilege Escalation", description="Injecting code into processes to elevate privileges", platforms=["Windows", "macOS", "Linux"]),
    MitreTechnique(technique_id="T1070.001", name="Clear Windows Event Logs", tactic="Defense Evasion", description="Clearing security event logs to evade detection", platforms=["Windows"]),
    MitreTechnique(technique_id="T1112", name="Modify Registry", tactic="Defense Evasion", description="Modifying registry entries to hide activity", platforms=["Windows"]),
    MitreTechnique(technique_id="T1018", name="Remote System Discovery", tactic="Discovery", description="Discovering remote hosts on the network", platforms=["Windows", "macOS", "Linux"])
]

def load_mitre_techniques() -> List[MitreTechnique]:
    try:
        res = httpx.get(ATTACK_STIX_URL, timeout=10.0)
        if res.status_code == 200:
            stix_data = res.json()
            techniques = []
            for obj in stix_data.get("objects", []):
                if obj.get("type") == "attack-pattern" and not obj.get("revoked", False):
                    tech_id = None
                    for ref in obj.get("external_references", []):
                        if ref.get("source_name") == "mitre-attack":
                            tech_id = ref.get("external_id")
                            break
                    if tech_id and re.match(r"^T\d{4}(\.\d{3})?$", tech_id):
                        tactic = "Unknown"
                        phases = obj.get("kill_chain_phases", [])
                        if phases:
                            tactic = phases[0].get("phase_name", "Unknown").replace("-", " ").title()
                        tech = MitreTechnique(
                            technique_id=tech_id,
                            name=obj.get("name", "Unknown"),
                            tactic=tactic,
                            description=obj.get("description", "")[:500],
                            platforms=obj.get("x_mitre_platforms", ["Windows"])
                        )
                        techniques.append(tech)
            if len(techniques) > 50:
                logger.info(f"Loaded {len(techniques)} MITRE techniques from STIX bundle.")
                return techniques
    except Exception as e:
        logger.warning(f"Could not load MITRE STIX online: {e}. Using default techniques.")

    return DEFAULT_TECHNIQUES
