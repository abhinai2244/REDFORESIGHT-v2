"""
SPL Query Templates targeting index=redforesight_range for Sysmon and Windows Event logs.
"""

INDEX = "redforesight_range"

HOST_ACTIVITY_SUMMARY = f"""
index={INDEX} host="{{host}}"
| stats count by sourcetype, EventCode
| sort - count
| head 20
"""

PROCESS_CREATION_EVENTS = f"""
index={INDEX} host="{{host}}" sourcetype="WinEventLog:Sysmon" EventCode=1
| table _time, Image, CommandLine, ParentImage, ParentCommandLine, User
| sort - _time
| head {{limit}}
"""

AUTH_EVENTS_IN_WINDOW = f"""
index={INDEX} host="{{host}}" sourcetype="WinEventLog:Security" (EventCode=4624 OR EventCode=4625)
| table _time, TargetUserName, TargetDomainName, LogonType, IpAddress, EventCode
| sort - _time
| head {{limit}}
"""

NETWORK_CONNECTIONS_FROM_HOST = f"""
index={INDEX} host="{{host}}" sourcetype="WinEventLog:Sysmon" EventCode=3
| table _time, Image, SourceIp, DestinationIp, DestinationPort, User
| sort - _time
| head {{limit}}
"""

REGISTRY_MODIFICATION_EVENTS = f"""
index={INDEX} host="{{host}}" sourcetype="WinEventLog:Sysmon" (EventCode=12 OR EventCode=13 OR EventCode=14)
| table _time, Image, TargetObject, Details, EventType, User
| sort - _time
| head {{limit}}
"""
