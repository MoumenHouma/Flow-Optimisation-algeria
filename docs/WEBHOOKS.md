# Webhooks (F10)

RouteOpt notifie vos systèmes lorsqu'un événement métier se produit, en
envoyant un `POST` JSON signé à chaque endpoint webhook actif. La livraison
est *best-effort* : un webhook lent ou en échec ne bloque jamais l'action qui
a produit l'événement.

## Configuration

Créez un endpoint dans **Développeurs → Webhooks** (ou via l'API applicative
`POST /api/v1/integrations/webhooks`, admin). Un **secret de signature** est
renvoyé **une seule fois** à la création ; il est chiffré au repos (Fernet) et
utilisé pour signer chaque envoi.

## Événements

| Événement | Déclencheur | Charge utile |
|---|---|---|
| `delivery.status_changed` | Une livraison change de statut | `delivery_id`, `status`, … |
| `optimization.completed` | Un job d'optimisation se termine | `job_id`, `trigger`, `total_distance_m`, `route_ids` |

Un endpoint peut s'abonner à des événements précis ou à `*` (tous).

## Format de la requête

En-têtes :

```
Content-Type: application/json
X-RouteOpt-Event: optimization.completed
X-RouteOpt-Signature: sha256=<hexdigest>
```

Corps (exemple) :

```json
{
  "job_id": "9f8d...",
  "trigger": "manual",
  "total_distance_m": 48213.5,
  "route_ids": ["a1...", "b2..."]
}
```

## Vérification de la signature

`X-RouteOpt-Signature` est un HMAC-SHA256 du **corps brut** avec votre secret,
préfixé de `sha256=`. Recalculez-le et comparez en temps constant **avant**
de traiter la charge utile.

### Python

```python
import hashlib
import hmac

def verify(secret: str, raw_body: bytes, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

### Node.js

```js
const crypto = require("crypto");

function verify(secret, rawBody, signatureHeader) {
  const expected =
    "sha256=" + crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signatureHeader));
}
```

> Signez et vérifiez toujours le corps **brut** (avant tout `JSON.parse`) :
> une re-sérialisation change les octets et invalide la signature.

## Bonnes pratiques

- Répondez `2xx` rapidement ; effectuez le traitement lourd en asynchrone.
- Rejetez les signatures invalides (`401`) sans traiter la charge.
- Traitez les événements de façon idempotente (une re-livraison est possible).
