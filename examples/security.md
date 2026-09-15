# Security finding

## `/showmewhy why`

```text
HIGH-RISK CONFIGURATION

The service is internet-reachable without an authentication boundary.

WHY

public ingress
     +
authentication disabled
     +
privileged operation
        ↓
unauthenticated privileged access

Evidence
- ingress rule permits public traffic
- authentication middleware is disabled
- endpoint performs privileged state changes

Confidence: HIGH
```
