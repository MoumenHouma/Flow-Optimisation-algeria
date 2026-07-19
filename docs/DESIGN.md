# DESIGN — UI/UX Design Document

> **Version** : 1.0.0  
> **Date** : 2026-07-19  
> **Designer** : Moumen Houma  
> **Style** : Clean, utilitaire, orienté données — inspiré de Linear, Notion, Mapbox Studio

---

## 1. Design Principles

### 1.1 Principes Fondamentaux

| Principe | Description | Application |
|----------|-------------|-------------|
| **Clarté avant beauté** | L'utilisateur doit comprendre immédiatement ce que fait l'outil | Dashboard avec métriques en premier plan |
| **Données actionnables** | Chaque écran doit permettre une action concrète | Bouton "Optimiser" toujours visible |
| **Feedback immédiat** | L'utilisateur sait ce qui se passe à chaque étape | Barre de progression, états de chargement |
| **Mobile-first pour livreurs** | L'app livreur est la plus utilisée en conditions réelles | PWA, offline, grandes zones tactiles |
| **Localisation** | Arabe (RTL), Français, Darja | Interface adaptée, adresses en arabe supportées |

### 1.2 Persona-Driven Design

**Khaled (Gérant de Flotte)** veut :
- Voir rapidement si ses livreurs respectent les horaires
- Planifier le lendemain en < 5 minutes
- Comprendre le ROI (distance économisée, carburant)

**Amine (Livreur)** veut :
- Savoir où aller, dans quel ordre, sans réfléchir
- Signaler un problème (adresse introuvable, client absent) en 1 tap
- Fonctionner sans connexion internet

---

## 2. Design System

### 2.1 Palette de Couleurs

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRIMARY PALETTE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Primary Blue    │  #2563EB  │  Actions principales, CTA    │
│  Primary Dark    │  #1D4ED8  │  Hover states                  │
│  Primary Light   │  #DBEAFE  │  Backgrounds, badges           │
│                                                                 │
│  Success Green   │  #10B981  │  Livré, optimisé, positif      │
│  Warning Amber   │  #F59E0B  │  En retard, attention          │
│  Danger Red      │  #EF4444  │  Échec, erreur, annulé         │
│  Info Cyan       │  #06B6D4  │  En cours, information         │
│                                                                 │
│  Neutral 900     │  #111827  │  Texte principal               │
│  Neutral 700     │  #374151  │  Texte secondaire              │
│  Neutral 500     │  #6B7280  │  Placeholder, disabled         │
│  Neutral 300     │  #D1D5DB  │  Bordures, dividers            │
│  Neutral 100     │  #F3F4F6  │  Backgrounds alternés          │
│  Neutral 50      │  #F9FAFB  │  Background principal          │
│                                                                 │
│  Map Primary     │  #3B82F6  │  Route optimisée               │
│  Map Secondary   │  #9CA3AF  │  Route alternative             │
│  Map Depot       │  #10B981  │  Point de départ               │
│  Map Stop        │  #2563EB  │  Livraison                     │
│  Map Stop Late   │  #EF4444  │  Livraison en retard           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Typographie

| Élément | Police | Taille | Poids | Ligne |
|---------|--------|--------|-------|-------|
| H1 (Page title) | Inter / Noto Sans Arabic | 24px | 700 | 1.3 |
| H2 (Section) | Inter / Noto Sans Arabic | 20px | 600 | 1.4 |
| H3 (Card title) | Inter / Noto Sans Arabic | 16px | 600 | 1.4 |
| Body | Inter / Noto Sans Arabic | 14px | 400 | 1.5 |
| Caption | Inter / Noto Sans Arabic | 12px | 400 | 1.4 |
| Mono (data) | JetBrains Mono | 13px | 400 | 1.4 |

**Font Stack** :
```css
--font-sans: 'Inter', 'Noto Sans Arabic', 'Segoe UI', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 2.3 Spacing System (4px base)

```
4px  -> xs   (micro gaps, icon padding)
8px  -> sm   (tight spacing, inline elements)
12px -> md   (card padding small)
16px -> base (default padding, gap)
24px -> lg   (section spacing)
32px -> xl   (page sections)
48px -> 2xl  (major sections)
64px -> 3xl  (hero spacing)
```

### 2.4 Composants Clés

#### Button Variants

```
┌─────────────────────────────────────────────────────────────────┐
│  Primary    │  [ Optimiser la tournée ]  │  bg-blue-600      │
│  Secondary  │  [ Importer CSV ]           │  bg-white border   │
│  Danger     │  [ Annuler ]                │  bg-red-600        │
│  Ghost      │  [ Voir détails -> ]         │  text only         │
│  Icon       │  [ ⚙️ ]                     │  square, icon only │
└─────────────────────────────────────────────────────────────────┘
```

#### Card Pattern

```
┌─────────────────────────────────────────┐
│  📦 Livraison #12345          [⋯]       │  ← Header with action
├─────────────────────────────────────────┤
│  12 Rue Didouche Mourad, Alger Centre   │  ← Content
│  🕐 10:00–12:00  |  📍 2.3 km          │
│  ⚖️ 5.2 kg  |  📐 0.3 m3             │
├─────────────────────────────────────────┤
│  [ Modifier ]  [ Supprimer ]            │  ← Footer actions
└─────────────────────────────────────────┘
```

#### Map Marker

```
     ┌───┐
     │ 3 │     ← Number = sequence in route
     └───┘
       │
       ▼
    (pin)      ← Color: Blue (on time), Red (late), Green (depot)
```

---

## 3. Wireframes & Flows

### 3.1 Flow Principal : Planifier une Tournée

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Step 1    │───▶│   Step 2    │───▶│   Step 3    │───▶│   Step 4    │
│   Import    │    │   Configure │    │   Optimize    │    │   Dispatch  │
│             │    │             │    │             │    │             │
│ [Upload CSV]│    │ [Véhicules] │    │ [▶ Lancer]  │    │ [📤 Envoyer]│
│             │    │ [Contraintes│    │             │    │ [📧 Email]  │
│ Preview     │    │  horaires]  │    │ Loading...  │    │ [📱 SMS]    │
│ table       │    │ [Dépôt]     │    │ Result map    │    │ [🔗 Share]  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 3.2 Écran : Dashboard Manager (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RouteOpt                              [🔔] [👤 Khaled] [⚙️]               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Aujourd'hui, 19 Juillet 2026                                       │   │
│  │                                                                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ 127 km   │  │ 8h 30min │  │ 45/50    │  │ 3/5      │           │   │
│  │  │ Distance │  │ Temps    │  │ Livré    │  │ Véhicules│           │   │
│  │  │ total    │  │ total    │  │          │  │ actifs   │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │   │
│  │                                                                     │   │
│  │  [📊 Voir rapport détaillé →]                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  🗺️ Carte des livraisons   │  │  📋 Tournées actives                │   │
│  │                             │  │                                     │   │
│  │  [MapLibre interactive]    │  │  ┌─────────────────────────────┐   │   │
│  │  • Routes colorées          │  │  │ 🚐 Véhicule 1 (Amine)       │   │   │
│  │  • Markers numérotés        │  │  │ 12/15 livraisons • 85%      │   │   │
│  │  • Dépôt vert               │  │  │ [▓▓▓▓▓▓▓▓▓▓░░░]           │   │   │
│  │                             │  │  │ Dernière: 12:30 — En route  │   │   │
│  │                             │  │  └─────────────────────────────┘   │   │
│  │                             │  │  ┌─────────────────────────────┐   │   │
│  │                             │  │  │ 🚐 Véhicule 2 (Karim)       │   │   │
│  │                             │  │  │ 8/10 livraisons • 80%       │   │   │
│  │                             │  │  │ [▓▓▓▓▓▓▓▓░░░░░░░]           │   │   │
│  │                             │  │  │ Dernière: 12:15 — Livré   │   │   │
│  │                             │  │  └─────────────────────────────┘   │   │
│  │                             │  │                                     │   │
│  └─────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📈 Performance cette semaine                                       │   │
│  │                                                                     │   │
│  │  Distance optimisée vs manuelle                                     │   │
│  │  [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓] │   │
│  │  -23% de distance parcourue • Économie estimée: 12 500 DA          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Écran : Optimisation (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Retour au dashboard    Optimisation #OPT-2026-07-19-001                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │  ⚙️ Paramètres              │  │  🗺️ Résultat optimisé             │   │
│  │                             │  │                                     │   │
│  │  Véhicules: 3               │  │  [Carte interactive]               │   │
│  │  ├─ 🚐 V1 (cap: 500kg)      │  │  • Route 1: Bleu                   │   │
│  │  ├─ 🚐 V2 (cap: 500kg)      │  │  • Route 2: Vert                   │   │
│  │  └─ 🚐 V3 (cap: 300kg)      │  │  • Route 3: Orange                 │   │
│  │                             │  │                                     │   │
│  │  Contraintes:               │  │  Distance totale: 127.5 km          │   │
│  │  ☑ Fenêtres horaires        │  │  Temps estimé: 8h 30min           │   │
│  │  ☑ Capacités                │  │  Véhicules utilisés: 3/3            │   │
│  │  ☑ Priorités                │  │                                     │   │
│  │                             │  │  [📥 Exporter PDF] [📥 Excel]        │   │
│  │  [▶ Re-optimiser]           │  │  [📤 Envoyer aux livreurs]         │   │
│  │  [⚙️ Paramètres avancés]    │  │                                     │   │
│  └─────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📋 Détails des tournées                                            │   │
│  │                                                                     │   │
│  │  🚐 Véhicule 1 — 45.2 km — 2h 50min                               │   │
│  │  ┌────┬─────────────────────────────┬──────────┬──────────┐        │   │
│  │  │ #  │ Adresse                     │ Horaire  │ Statut   │        │   │
│  │  ├────┼─────────────────────────────┼──────────┼──────────┤        │   │
│  │  │ 1  │ 12 Rue Didouche Mourad      │ 09:00    │ ⏳ Planifié│        │   │
│  │  │ 2  │ 45 Bd Mohamed VI            │ 09:25    │ ⏳ Planifié│        │   │
│  │  │ 3  │ 8 Rue Hassiba Ben Bouali    │ 09:50    │ ⏳ Planifié│        │   │
│  │  │ ...│                             │          │          │        │   │
│  │  └────┴─────────────────────────────┴──────────┴──────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Écran : Driver PWA (Mobile)

```
┌─────────────────┐
│  RouteOpt 📦    │  ← Header sticky
│  ───────────────│
│                 │
│  🚐 Tournée #1  │
│  12/15 livrées  │
│  [▓▓▓▓▓▓▓▓▓▓░░░]│
│                 │
│  ┌─────────────┐│
│  │  ⬆️ Swipe   ││  ← Current delivery card
│  │  #3 sur 15  ││
│  │             ││
│  │  📍 12 Rue  ││
│  │  Didouche   ││
│  │  Mourad     ││
│  │             ││
│  │  🕐 09:00–  ││
│  │  12:00      ││
│  │  ⚖️ 5.2 kg  ││
│  │             ││
│  │  [📞 Appeler]││
│  │  [🧭 Naviguer]││
│  └─────────────┘│
│                 │
│  ┌─────────────┐│
│  │  [✅ Livré]  ││  ← Big action buttons
│  │  [❌ Échec]  ││
│  │  [📸 Photo]  ││
│  └─────────────┘│
│                 │
│  [≡ Liste] [⚙️] │  ← Bottom nav
└─────────────────┘
```

### 3.5 Écran : Import CSV (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Retour    Importer les livraisons                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📁 Glissez votre fichier CSV/Excel ici                            │   │
│  │                                                                     │   │
│  │  ou [ Parcourir ]                                                   │   │
│  │                                                                     │   │
│  │  Format attendu: address, time_window_start, time_window_end,     │   │
│  │  weight, volume, priority, phone                                  │   │
│  │  [📥 Télécharger le modèle →]                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ✅ 45 livraisons importées                                          │   │
│  │                                                                     │   │
│  │  ┌────┬─────────────────────────────┬──────────┬──────────┐        │   │
│  │  │ #  │ Adresse                     │ Horaire  │ ⚠️       │        │   │
│  │  ├────┼─────────────────────────────┼──────────┼──────────┤        │   │
│  │  │ 1  │ 12 Rue Didouche Mourad      │ 09:00–12 │ ✓ OK     │        │   │
│  │  │ 2  │ 45 Bd Mohamed VI            │ 10:00–14 │ ✓ OK     │        │   │
│  │  │ 3  │ [Adresse non trouvée]       │ 08:00–10 │ ⚠️ Corriger│       │   │
│  │  │ ...│                             │          │          │        │   │
│  │  └────┴─────────────────────────────┴──────────┴──────────┘        │   │
│  │                                                                     │   │
│  │  [⚠️ Corriger 3 adresses]  [▶ Continuer avec 42 valides]          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Interactions & Animations

### 4.1 Loading States

```
Optimisation en cours...
┌─────────────────────────────────────────┐
│  [████████████████░░░░░░░░░░░░░░░░░░]  │  ← Progress bar
│  45 livraisons • 3 véhicules            │
│  Temps estimé: ~8 secondes              │
│                                         │
│  [ Annuler ]                            │
└─────────────────────────────────────────┘
```

### 4.2 Success Animation

```
Tournée optimisée ! 🎉
┌─────────────────────────────────────────┐
│                                         │
│           ✓                             │
│          /│\                           │  ← Animated checkmark
│         / │ \                          │
│           │                             │
│          / \                           │
│         /   \                          │
│                                         │
│  Distance: 127.5 km (-23% vs manuel)   │
│  Temps: 8h 30min                        │
│  Véhicules: 3                           │
│                                         │
│  [ Voir la carte ]  [ Exporter ]        │
└─────────────────────────────────────────┘
```

### 4.3 Error States

```
┌─────────────────────────────────────────┐
│  ⚠️ Optimisation impossible             │
│                                         │
│  Certains contraintes sont incompatibles:│
│  • Livraison #12: fenêtre 08:00–09:00   │
│    trop éloignée du dépôt                │
│  • Véhicule 1: capacité dépassée        │
│                                         │
│  [ Modifier les contraintes ]            │
│  [ Ignorer et optimiser partiellement ]  │
└─────────────────────────────────────────┘
```

---

## 5. Responsive Breakpoints

| Breakpoint | Width | Usage |
|------------|-------|-------|
| **xs** | < 480px | Mobile portrait (Driver PWA) |
| **sm** | 480–768px | Mobile landscape, small tablets |
| **md** | 768–1024px | Tablets, small laptops |
| **lg** | 1024–1440px | Desktop standard (Manager) |
| **xl** | > 1440px | Large desktop, dashboards |

### 5.1 Adaptations Mobile

- **Dashboard** : Carte plein écran, cards empilées verticalement
- **Optimisation** : Stepper vertical, paramètres dans un drawer
- **Driver PWA** : Tout en une colonne, boutons > 48px (touch target)

---

## 6. RTL (Right-to-Left) — Arabe

### 6.1 Règles RTL

```css
[dir="rtl"] {
  --text-align: right;
  --flex-direction: row-reverse;
  --margin-start: margin-right;
  --margin-end: margin-left;
}

/* MapLibre RTL support */
map.setRTLTextPlugin('https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-rtl-text/v0.2.3/mapbox-gl-rtl-text.js');
```

### 6.2 Layout RTL

```
LTR (Français)          RTL (Arabe)
┌─────────────────┐     ┌─────────────────┐
│ [Logo]  Menu    │     │  Menu  [Logo]   │
│ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │ Text ->      │ │     │ │      <- Text │ │
│ │ [Button]    │ │     │ │    [Button] │ │
│ └─────────────┘ │     │ └─────────────┘ │
└─────────────────┘     └─────────────────┘
```

---

## 7. Accessibility (a11y)

### 7.1 Standards

- **WCAG 2.1 AA** : Contrast ratio 4.5:1 minimum
- **Keyboard navigation** : Tab order logique, focus visible
- **Screen readers** : ARIA labels sur tous les éléments interactifs
- **Color blindness** : Pas d'information uniquement par couleur (icônes + texte)

### 7.2 Exemples

```html
<!-- Map marker with full accessibility -->
<button 
  aria-label="Livraison #3, 12 Rue Didouche Mourad, Alger, fenêtre 09:00-12:00"
  class="map-marker"
  tabindex="0"
>
  <span class="marker-number">3</span>
  <span class="marker-status" aria-hidden="true">⏳</span>
</button>

<!-- Progress bar -->
<div role="progressbar" aria-valuenow="45" aria-valuemax="50" aria-label="45 livraisons sur 50 effectuées">
  <div class="progress-fill" style="width: 90%"></div>
</div>
```

---

## 8. Assets & Icons

### 8.1 Icon System (Lucide React)

| Icon | Usage | Nom Lucide |
|------|-------|-----------|
| 📦 | Livraison | `Package` |
| 🚐 | Véhicule | `Truck` |
| 📍 | Localisation | `MapPin` |
| 🕐 | Horaire | `Clock` |
| ⚖️ | Poids | `Scale` |
| 📐 | Volume | `Box` |
| ✅ | Livré | `CheckCircle` |
| ❌ | Échec | `XCircle` |
| ⚠️ | Attention | `AlertTriangle` |
| 📊 | Stats | `BarChart3` |
| 📥 | Import | `Download` |
| 📤 | Export | `Upload` |
| 🧭 | Navigation | `Navigation` |
| 📞 | Appeler | `Phone` |
| 📸 | Photo | `Camera` |
| ⚙️ | Paramètres | `Settings` |
| 🔍 | Rechercher | `Search` |
| 📋 | Liste | `List` |
| 🗺️ | Carte | `Map` |

---

*Design system basé sur Tailwind CSS + shadcn/ui pour rapidité de développement.*
