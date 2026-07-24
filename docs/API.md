# API partenaire publique (F10)

API REST authentifiée par clé, destinée aux intégrations e-commerce
(Shopify, WooCommerce, ERP…). Elle est **distincte** de l'API applicative
authentifiée par session JWT : les partenaires intègrent sans compte utilisateur.

- Base URL : `https://<votre-hôte>/api/public/v1`
- Format : JSON (`Content-Type: application/json`)
- Référence interactive : `https://<votre-hôte>/docs` (OpenAPI/Swagger)

## Authentification

Chaque requête porte l'en-tête `X-API-Key` :

```
X-API-Key: <VOTRE_CLE_API>
```

Les clés se créent dans **Développeurs → Clés API** (ou via l'API applicative
`POST /api/v1/integrations/api-keys`, réservée aux admins). La clé en clair
n'est affichée **qu'une seule fois** à la création ; seule son empreinte
SHA-256 est stockée. Une clé révoquée est refusée immédiatement (`401`).

### Portées (scopes)

| Scope | Autorise |
|---|---|
| `read` | Lecture des livraisons |
| `write` | `read` + création de livraisons |
| `admin` | `write` + opérations d'administration |

Une portée insuffisante renvoie `403`.

## Limites de débit

Fixe : **600 requêtes / minute par clé** (fenêtre glissante d'une minute).
Un dépassement renvoie `429 Too Many Requests` — réessayez après la fenêtre.

## Endpoints

### `POST /deliveries` — créer une livraison *(scope `write`)*

Si `lat`/`lon` sont absents, l'adresse est géocodée de façon asynchrone
(`geocoding_status` passe de `pending` à `success`/`failed`).

Corps :

| Champ | Type | Requis | Notes |
|---|---|---|---|
| `order_id` | string | non | Référence côté partenaire (≤ 100) |
| `address` | string | **oui** | Adresse de livraison |
| `address_locale` | string | non | `fr` (défaut) / `ar` |
| `lat`, `lon` | number | non | Fournis ⇒ pas de géocodage |
| `customer_phone` | string | non | ≤ 30 caractères |
| `time_window_start`, `time_window_end` | `HH:MM` | non | Fenêtre horaire |
| `weight` | number | non | ≥ 0 |
| `priority` | int | non | 1–3 (défaut 1) |

```bash
curl -X POST https://votre-hote/api/public/v1/deliveries \
  -H "X-API-Key: $ROUTEOPT_API_KEY" -H "Content-Type: application/json" \
  -d '{"order_id":"CMD-1042","address":"12 Rue Didouche Mourad, Alger","weight":5}'
```

Réponse `201` :

```json
{
  "id": "b1c2...",
  "order_id": "CMD-1042",
  "address": "12 Rue Didouche Mourad, Alger",
  "lat": null, "lon": null,
  "geocoding_status": "pending",
  "status": "pending",
  "created_at": "2026-07-22T09:00:00+00:00"
}
```

### `GET /deliveries/{id}` — suivre une livraison *(scope `read`)*

Renvoie l'état courant. `404` si la livraison n'appartient pas à la société de la clé.

### `GET /deliveries?limit=50` — lister les livraisons récentes *(scope `read`)*

Les plus récentes d'abord ; `limit` entre 1 et 200 (défaut 50).

## Codes d'erreur

| Code | Signification |
|---|---|
| `401` | Clé absente, invalide ou révoquée |
| `403` | Portée insuffisante |
| `404` | Ressource hors périmètre de la clé |
| `422` | Corps invalide |
| `429` | Limite de débit dépassée |

Pour les notifications sortantes (statut de livraison, optimisation terminée),
voir [`WEBHOOKS.md`](./WEBHOOKS.md).
