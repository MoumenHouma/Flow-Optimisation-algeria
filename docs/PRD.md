# PRD — Product Requirements Document

## RouteOpt — Optimiseur de Tournées de Livraison pour le Marché Algérien

> **Version** : 1.0.0  
> **Date** : 2026-07-19  
> **Auteur** : Moumen Houma  
> **Domaine** : Modélisation, Optimisation & Aide à la Décision (Master)

---

## 1. Vision & Objectif

### 1.1 Problème
Les livreurs et flottes algériennes (e-commerce, restauration, logistique) planifient leurs tournées **manuellement** ou via des solutions étrangères **inadaptées** (coût, langue, données cartographiques inexactes pour l'Algérie). Cela engendre :
- 20–40% de kilométrage inutile (out-of-route miles)
- Retards chroniques et fenêtres de livraison manquées
- Surcharge de certains véhicules, sous-utilisation d'autres
- Coûts de carburant et d'usure disproportionnés

### 1.2 Solution
**RouteOpt** est une plateforme SaaS d'optimisation de tournées de livraison, spécifiquement conçue pour le contexte algérien :
- **Cartographie** : OpenStreetMap (OSRM auto-hébergé) pour des données routières précises et gratuites
- **Optimisation** : Google OR-Tools (VRP solver) pour la résolution du problème de tournées de véhicules
- **Prix** : Modèle SaaS abordable (freemium → abonnement par véhicule/mois)
- **Langue** : Arabe, Français, Darja (support local)

### 1.3 Objectifs Quantitatifs (KPIs)

| KPI | Cible 6 mois | Cible 12 mois |
|-----|-------------|---------------|
| Réduction distance totale | 15% | 25% |
| Respect fenêtres horaires | 85% | 92% |
| Temps de résolution (< 50 livraisons) | < 5s | < 3s |
| Taux d'adoption (pilotes) | 5 flottes | 20 flottes |
| NPS utilisateurs | > 40 | > 50 |

---

## 2. Public Cible & Personas

### 2.1 Persona Principal : "Khaled le Gérant de Flotte"
- **Profil** : Gère 8–15 véhicules de livraison pour un e-commerce ou une chaîne de restauration
- **Pain points** : Planning manuel le soir pour le lendemain, appels constants des clients, pénuries de carburant
- **Tech level** : Basique — veut un outil simple, pas un tableau Excel complexe
- **Budget** : 5 000–15 000 DA/mois maximum pour l'outil

### 2.2 Persona Secondaire : "Amine le Livreur Indépendant"
- **Profil** : Livreur à son compte, 20–30 livraisons/jour via plusieurs plateformes
- **Pain points** : Perd du temps à chercher les adresses, se trompe d'ordre de passage
- **Tech level** : Smartphone uniquement
- **Budget** : Gratuit ou très bas coût

### 2.3 Persona Tertiaire : "Sofiane le DSI d'Entreprise"
- **Profil** : DSI d'une grande distribution ou d'une pharmacie en chaîne
- **Pain points** : Besoin d'intégration API, SLA stricts, reporting
- **Tech level** : Avancé — veut API REST, webhooks, SSO
- **Budget** : Budget IT dédié, prêt à payer pour l'enterprise

---

## 3. Fonctionnalités — MVP & Roadmap

### 3.1 MVP (Phase 1 — 8 semaines)

| ID | Fonctionnalité | Priorité | Description |
|----|---------------|----------|-------------|
| F1 | Import livraisons (CSV/Excel) | P0 | Upload simple de fichier avec adresses, fenêtres horaires, poids/volume |
| F2 | Géocodage adresses | P0 | Conversion adresse texte → coordonnées GPS (Nominatim OSM) |
| F3 | Optimisation tournées (OR-Tools) | P0 | Résolution VRP avec capacités, fenêtres horaires, minimisation distance |
| F4 | Visualisation carte (MapLibre) | P0 | Affichage des tournées optimisées sur carte interactive |
| F5 | Export routes (PDF/Excel) | P0 | Export des itinéraires pour le livreur (ordre + adresses) |
| F6 | Dashboard simple | P1 | Vue d'ensemble : distance totale, nombre véhicules, temps estimé |
| F7 | Gestion flotte basique | P1 | Ajout/suppression véhicules avec capacité et point de départ |

### 3.2 Phase 2 (4–6 mois)

| ID | Fonctionnalité | Description |
|----|---------------|-------------|
| F8 | App livreur (PWA) | Itinéraire turn-by-turn, preuve de livraison (photo + signature), statut en temps réel |
| F9 | Re-optimisation dynamique | Recalcul si livraison annulée, retard, ou nouvelle commande urgente |
| F10 | API REST publique | Intégration e-commerce (Shopify, WooCommerce, systèmes locaux) |
| F11 | Analytics & rapports | KPIs historiques, tendances, comparaison avant/après optimisation |
| F12 | Multi-dépôt | Support de plusieurs entrepôts/points de départ |

### 3.3 Phase 3 (6–12 mois)

| ID | Fonctionnalité | Description |
|----|---------------|-------------|
| F13 | Prédiction temps de service | ML basé sur historique (type client, quartier, heure) |
| F14 | Optimisation multi-objectif | Minimiser distance + temps + coût carburant + émissions CO2 |
| F15 | Territory management | Division automatique en zones géographiques + assignation livreurs |
| F16 | White-label | Personnalisation marque pour grands clients |

---

## 4. Contraintes Métier Spécifiques Algérie

### 4.1 Contraintes Opérationnelles
- **Pénurie carburant** : Les livreurs peuvent être bloqués. Le système doit permettre la re-planification rapide.
- **Adresses imprécises** : Beaucoup d'adresses algériennes manquent de numéro de rue précis. Le géocodage doit tolérer les approximations.
- **Connexion intermittente** : Les zones rurales ont une 3G/4G instable. L'app livreur doit fonctionner offline avec sync différée.
- **Langue** : Interface en arabe (RTL), français, et support darja pour les adresses.
- **Paiement** : Support CCP, BaridiMob, et paiement à la livraison (pas de CB omniprésente).

### 4.2 Contraintes Réglementaires
- **Horaires de travail** : Respect des 35h hebdomadaires (droit algérien du travail) pour les livreurs salariés.
- **Véhicules** : Possibilité de flottes mixtes (voitures, camions, motos) avec contraintes de permis.
- **Données personnelles** : Conformité CNIL (loi 18-07 relative à la protection des données personnelles).

### 4.3 Contraintes Techniques
- **OSM Algérie** : Couverture variable selon les régions. Fallback sur approximation si données manquantes.
- **OSRM** : Prétraitement nécessaire pour l'Algérie (~2–4 GB de données, RAM requise ~8–16 GB).
- **Hébergement** : Serveur en Algérie (pour latence) ou cloud EU (pour coût). Hybride recommandé.

---

## 5. Modèle Économique

### 5.1 Pricing Tiers

| Plan | Prix | Inclus | Cible |
|------|------|--------|-------|
| **Free** | 0 DA | 1 véhicule, 10 livraisons/jour, optimisation basique | Livreurs indépendants, test |
| **Starter** | 2 500 DA/mois | 5 véhicules, 100 livraisons/jour, CSV import, carte | Petites flottes |
| **Pro** | 7 500 DA/mois | 20 véhicules, 500 livraisons/jour, API, analytics | E-commerce, chaînes |
| **Enterprise** | Sur devis | Illimité, multi-dépôt, white-label, SLA, support dédié | Grandes distributions |

### 5.2 Métriques Économiques
- **CAC** (Coût d'Acquisition Client) : ~15 000 DA (via Facebook/LinkedIn ads + partenariats incubateurs)
- **LTV** (Lifetime Value) : ~45 000 DA (Starter moyen 6 mois, Pro moyen 12 mois)
- **LTV/CAC ratio** : Cible > 3

---

## 6. Risques & Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| OSM Algérie incomplet | Moyenne | Élevé | Fallback géocodage, crowdsourcing corrections, partenariat OSM Algeria |
| Adoption lente (habitude Excel) | Élevée | Élevé | Onboarding guidé, import Excel one-click, ROI visible immédiatement |
| Concurrence Yassir/Temtem | Moyenne | Moyen | Différenciation B2B/SaaS vs B2C, API ouverte, verticalisation |
| Pénurie serveur cloud Algérie | Faible | Moyen | Hébergement hybride (Algérie + EU), edge caching |
| Temps de résolution OR-Tools | Moyenne | Moyen | Décomposition géographique, warm-start, limites de temps configurables |

---

## 7. Succès & Adoption

### 7.1 Critères de Succès MVP
- 5 flottes pilotes actives avec > 80% de satisfaction
- Temps moyen de résolution < 10s pour 30 livraisons
- Réduction mesurable de 15%+ de distance par rapport au planning manuel

### 7.2 Indicateurs de Traction
- Nombre de livraisons optimisées/jour
- Taux de rétention mensuelle (MRR churn < 5%)
- Nombre de livraisons réussies en première tentative
- Réduction CO2 estimée (marketing ESG)

---

## 8. Références & Benchmarks

- **Route4Me** (USA) : SaaS SMB, ~30–150$/véhicule/mois — interface simple, mais cher pour l'Algérie
- **OptimoRoute** (Croatie) : SaaS mid-market, API ouverte, bon modèle technique à suivre
- **Locus** (Inde) : AI-driven, enterprise — trop complexe/costly pour le MVP
- **OR-Tools** (Google) : Solver open-source, CP-SAT + metaheuristiques, benchmark 0.02s pour 17 nœuds
- **OSRM** : Routing engine C++, CH/MLD, < 5ms par requête, RAM 8–16 GB pour l'Algérie
- **AWS Sample** : Architecture de référence VRP avec OptaPlanner + GraphHopper + React

---

*Document vivant — mise à jour mensuelle selon retours utilisateurs et métriques.*
