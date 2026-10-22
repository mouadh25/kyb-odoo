# KYB pour Odoo — Manuel Utilisateur & Guide Pratique
**Version :** `2.0.0` / `20.0.2.0.0`  
**Cible :** Directeurs Financiers (DAF), Responsables Comptables, Gestionnaires Achats & Ventes  
**Portail KYB (by Digidev) :** [kyb.digidevagency.dz](https://kyb.digidevagency.dz)  
**Compatibilité :** Odoo 16.0 LTS, 17.0, 18.0, 19.0, 20.0 (Community & Enterprise)

---

## 1. À propos du module KYB (Version 2.0.0)

Le module **KYB pour Odoo** facilite l'identification de vos tiers et accompagne la mise en conformité fiscale de vos pièces comptables en Algérie :

* **Installation & Mises à Jour Autonomes en 1 Clic :**  
  * **Odoo Apps Store :** Téléchargement et activation directe en un clic sur votre instance sans modification de votre infrastructure.
  * **Moteur d'Upgrade Autonome :** Détection et application automatique des patchs et montées de version directement depuis l'interface Odoo (**Paramètres → KYB Compliance**), sans aucune commande terminal ni accès SSH.
* **Recherche & Auto-complétion Prédictive Instantanée (<10ms) :**
  * **Pour les Personnes Morales (Sociétés) :** Recherche intuitive par raison sociale ou nom commercial (ex: `CEVITAL`) avec auto-complétion instantanée connectée directement aux **portails gouvernementaux publics en direct** (incluse en consultation prédictive sans décompte de crédits).
  * **Pour toutes les entités (Personnes Morales & Personnes Physiques) :** Recherche universelle immédiate par identifiants officiels : **Numéro RC**, **NIF (15 chiffres)** ou **NIS**.
* **Enrichissement Fiscal & Légal Certifié en 1 Clic :**  
  Renseignement automatique et structuré des informations officielles : Raison sociale, Forme juridique, NIF (15 chiffres), Registre de Commerce (normalisé Décret 05-468), NIS, Capital social, Dirigeants, Adresse du siège et nomenclature d'activités NAE (principale et secondaires).
* **Vérification de Statut Juridique en Temps Réel :**  
  Consultation en direct de l'état d'activité officiel de chaque partenaire (**Actif**, **Radié**, **Suspendu**) avec inscription d'une note d'audit horodatée dans le fil de discussion (Chatter) pour assurer la traçabilité interne.
* **Assistance au Contrôle Temporel des Factures :**
  * **Achats Fournisseurs :** Contrôle temporel automatique comparant la date d'émission de la facture et le statut d'activité répertorié du fournisseur. Alerte ou blocage configurable en cas de fournisseur radié, contribuant à la protection de la déductibilité de vos charges et de la TVA (Articles 169 & 176 CIDTA / 30 CTCA).
  * **Ventes Clients :** Aide à l'édition de factures comportant les mentions légales obligatoires requises (Décret 05-468) et fiabilisation des données pour votre état 104 des clients.
* **Prévention Proactive des Doublons Fiscaux :**  
  Alerte immédiate à la saisie si un NIF existe déjà dans votre base, évitant l'éclatement des comptes auxiliaires et préservant l'organisation de votre grand livre.
* **Hébergement Souverain & Télémétrie Flotte (Loi 25-11) :**  
  Infrastructure 100% souveraine opérée au Datacenter d'Algérie Télécom, garantissant le respect de la Loi 18-07 et de la Loi 25-11 sur la résidence des données. Diagnostic de flotte zéro-PII assurant le maintien de la sécurité et la conformité du connecteur.

---

## 2. Configuration Rapide & Personnalisation des Politiques de Contrôle

La mise en service du connecteur s'effectue en moins de deux minutes dans les paramètres d'Odoo. Le module s'adapte à la politique de gestion des risques de votre entreprise (mode bloquant ou mode alerte).

### Étape 1 : Installation en 1 Clic via l'Odoo Apps Store
1. Dans votre instance Odoo, rendez-vous dans le menu **Applications**.
2. Recherchez `KYB` ou téléchargez le connecteur directement depuis **l'Odoo Apps Store**.
3. Cliquez sur **Activer** (ou **Installer**). Le module s'initialise automatiquement sans redémarrage de serveur.

### Étape 2 : Obtenir votre Clé d'API KYB (Essai Pilote Offert)
1. Rendez-vous sur le portail institutionnel :  
   👉 **[https://kyb.digidevagency.dz](https://kyb.digidevagency.dz)**
2. Renseignez vos coordonnées pour activer votre accès pilote de 7 jours ou connectez-vous à votre espace client.
3. Accédez à la rubrique **Clés API & Intégrations** et générez votre clé de production (format `sk_live_...`).

### Étape 3 : Activer la passerelle dans Odoo
1. Rendez-vous dans **Paramètres → KYB Compliance** (ou **Conforme KYB → Configuration**).
2. Renseignez les deux champs d'accès :
   * **API Key :** Collez votre clé secrète. Dans l'interface, celle-ci s'affiche sous forme masquée (`•••••••••••••••••••••••••••`) afin de protéger vos identifiants d'entreprise contre toute indiscrétion visuelle.
   * **Gateway URL :** Conservez l'adresse officielle de la passerelle en clair :  
     `https://kyb.digidevagency.dz`
3. **Mises à jour autonomes (v2.0.0) :** Un bouton **Vérifier les mises à jour** vous permet de déployer en 1 clic les nouvelles fonctionnalités et évolutions réglementaires sans intervention technique.

![Configuration des identifiants et politiques KYB](screenshots/05_kyb_settings_configuration.png)
*Figure 1 : Interface de configuration KYB affichant la passerelle officielle en clair et la clé API masquée.*

### Étape 4 : Choisir le niveau de rigueur de vos politiques (Au choix de l'entreprise)

Le module offre un contrôle granulaire pour s'adapter à la gouvernance de chaque direction financière :

| Paramètre | Options Disponibles | Comportement & Recommandation |
| :--- | :--- | :--- |
| **Politique de Validation des Factures** (*Action on Deregistered Supplier*) | • **Blocage Strict (Par défaut / Recommandé)**<br>• **Avertissement (Soft Warning)** | **• Blocage Strict :** Empêche la confirmation comptable (`Confirmer`) d'une facture si le fournisseur était radié des registres officiels à la date d'émission. Vise à prévenir le risque de rejet fiscal (CIDTA 169/176 & CTCA 30).<br>**• Avertissement :** Permet la validation pour les cas d'exception (ex: règlement d'un litige en cours), tout en inscrivant une alerte explicite dans le fil d'audit (Chatter). |
| **Détection des Doublons Fiscaux (NIF)** (*Duplicate NIF Policy*) | • **Avertissement (Par défaut)**<br>• **Blocage Strict**<br>• **Ignorer** | **• Avertissement :** Signale immédiatement la présence du contact existant avec un lien direct.<br>**• Blocage Strict :** Empêche l'enregistrement d'un second contact ayant un NIF identique via une exception bloquante.<br>**• Ignorer :** Tolère les doublons pour structures multi-établissements autorisées. |
| **Politique Fournisseurs Non Vérifiés** (*Action on Unverified Supplier*) | • **Autoriser avec avertissement (Par défaut)**<br>• **Exiger la vérification préalable** | **• Autoriser :** Laisse passer la saisie avec un badge "Non Vérifié".<br>**• Exiger :** Impose une vérification préalable sur les registres officiels avant d'autoriser la validation d'une facture. |
| **Audit Automatique de Clôture (G50)** (*End-of-Month Global Audit*) | • **Coché (Par défaut)**<br>• Décoché | Exécute une vérification globale automatisée de toutes les factures d'achat du mois en cours à une date paramétrable (par défaut le **18 du mois**, avant l'échéance légale du 20). |
| **Suivi des Versions & Mises à Jour en 1 Clic** (*Version Controls & Upgrade*) | • **Version Installée :** `2.0.0`<br>• **Dernière Version :** `2.0.0`<br>• **Dernière Télémétrie :** Date/Heure | Affiche en direct l'état de votre connecteur. Deux boutons permettent de contrôler le cycle de vie :<br>• **Vérifier les Mises à Jour :** Interroge la passerelle souveraine et synchronise l'état d'intégrité.<br>• **Mettre à jour maintenant (1-Clic) :** Télécharge la version certifiée et met à jour le module sans redémarrage. |
| **Mise à Jour Automatique des Correctifs** (*Auto-Update Minor Patches*) | • **Coché**<br>• **Décoché (Par défaut)** | Lorsque cochée, applique automatiquement les correctifs de sécurité mineurs et adaptations réglementaires urgentes lors de la tâche planifiée nocturne. |

---

### 2.1 Moteur Autonome de Mises à Jour & Distribution Certifiée (Version 2.0.0)

La version **2.0.0 (Autonomous Engine)** introduit un dispositif inédit de distribution et de mise à jour in-app directe depuis la passerelle souveraine de production (`kyb.digidevagency.dz`), éliminant définitivement les contraintes de déploiement manuel en ligne de commande ou d'intervention technique sur les serveurs d'hébergement.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Instance Odoo (Client)                           │
│                         (Paramètres → KYB Compliance)                       │
│                                                                             │
│   [ Vérifier les Mises à Jour ] ─────► (1) GET /api/v1/version              │
│                                                   │                         │
│   [ Mettre à jour maintenant  ] ─────► (2) GET /api/v1/downloads/kyb_odoo.zip
│                 │                                                           │
│                 ▼                                                           │
│   1. Contrôle d'Intégrité de l'Archive (__manifest__.py validé en mémoire)  │
│   2. Remplacement Atomique POSIX dans /mnt/extra-addons/kyb_odoo            │
│   3. Migration In-Band ORM (ir.module.module.button_immediate_upgrade)       │
│   4. Préservation 100% Intégrale des Données, Colonnes & Audit Chatter      │
│   5. Rechargement Dynamique de Session (/web) sans interruption de service  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ HTTPS (Port 443 / Bearer Token)
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Passerelle Souveraine KYB (by Digidev Agency)               │
│                         https://kyb.digidevagency.dz                        │
│                                                                             │
│   • Registre Central des Versions : Comparaison SemVer normalisée           │
│   • Dépôt Certifié des Paquets : Distribution d'archives validées           │
│   • Ingestion Télémétrie Flotte : Surveillance d'intégrité (Loi 25-11)      │
│                                                                             │
│              [ Datacenter Algérie Télécom — Hébergement Souverain ]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### A. Fonctionnement de la Détection de Version & Notification Visuelle
1. **Interrogation Manuelle en 1 Clic :**  
   À tout moment, depuis **Paramètres → KYB Compliance**, cliquez sur le bouton **Vérifier les Mises à Jour** (`action_check_kyb_update`).
2. **Dialogue avec la Passerelle Souveraine :**  
   Le connecteur interroge en HTTPS l'endpoint officiel `GET /api/v1/version` (ou `POST /api/v1/client/telemetry` lorsque la clé API est renseignée). L'algorithme normalise les numéros de version (suppression des préfixes de version Odoo tels que `16.0.`, `17.0.`, `20.0.`) pour garantir une comparaison sémantique déterministe (SemVer).
3. **Retour Utilisateur Immédiat (Notification Odoo) :**
   * **Connecteur à jour :** Une bannière verte confirme :  
     `« Votre connecteur KYB est parfaitement à jour (v2.0.0). »`
   * **Nouvelle version disponible :** Une bannière d'avertissement jaune détaille les évolutions réglementaires du journal des modifications (*Changelog*) et active le bouton d'action :  
     `« Nouvelle version 2.0.1 disponible ! Cliquez sur 'Mettre à jour maintenant'. »`

#### B. Déploiement en 1 Clic (`action_upgrade_kyb_module`)
Lorsque l'administrateur confirme le déploiement via le bouton **Mettre à jour maintenant (1-Clic)** :
1. **Téléchargement sécurisé et contrôlé :** Le connecteur télécharge l'archive officielle depuis l'adresse dédiée :  
   `https://kyb.digidevagency.dz/api/v1/downloads/kyb_odoo.zip`.
2. **Contrôle d'intégrité binaire :** L'archive est vérifiée en mémoire tampon (`io.BytesIO`). Le système contrôle formellement la présence du descripteur officiel `__manifest__.py`. Si l'archive est incomplète, le processus s'interrompt immédiatement sans toucher au module existant.
3. **Remplacement atomique des fichiers (Gestion POSIX sécurisée) :**  
   Pour éviter les erreurs courantes de collision de droits (`PermissionError: [Errno 13] Permission denied`) observées dans les conteneurs Linux exécutés sous utilisateur non-root (`odoo:odoo`), le connecteur supprime préventivement chaque fichier cible avant copie (`os.remove`).
4. **Migration in-band de la base de données :**  
   Le connecteur invoque la méthode native Odoo `button_immediate_upgrade()` sur le module `kyb_odoo`. PostgreSQL applique instantanément les nouvelles colonnes DDL, recharge les vues XML et synchronise les modèles sans nécessiter de redémarrage du conteneur ou du service Odoo.
5. **Rechargement fluide de l'interface :** Odoo renvoie une action client rechargeant la session utilisateur (`/web`) avec la nouvelle version active.

#### C. Mises à Jour Automatiques en Arrière-Plan (Patchs Réglementaires Silencieux)
* **Tâche Planifiée Quotidienne :** Le connecteur installe une tâche cron native Odoo (`ir_cron_kyb_telemetry_sync`) exécutée quotidiennement.
* **Application Silencieuse des Correctifs :** Lorsque la case **Mise à jour automatique des correctifs mineurs** (`auto_update_patches`) est cochée dans les paramètres, tout correctif mineur de sécurité ou adaptation d'urgence (ex: ajustement de formulaire CNRC ou mise à jour de nomenclature NAE) est automatiquement téléchargé et déployé en arrière-plan sans aucune action manuelle requise.
* **Mise à Niveau Forcée (Emergency Flag) :** En cas d'évolution réglementaire impérative dictée par l'administration fiscale ou le CNRC, la passerelle peut émettre l'indicateur `force_upgrade: true`. Le connecteur applique alors le correctif dès le battement de cœur suivant pour garantir la continuité de conformité de votre entreprise.

#### D. Préservation Absolue des Données & Règle d'Or Opérationnelle

> [!CAUTION]
> **RÈGLE D'OR D'EXPLOITATION : NE JAMAIS CLIQUER SUR « DÉSINSTALLER » !**  
> Dans l'architecture Odoo, désinstaller un module déclenche l'exécution d'instructions SQL irréversibles (`ALTER TABLE ... DROP COLUMN`) sur l'ensemble des colonnes ajoutées par ce module.  
> Si un utilisateur clique sur *Désinstaller*, PostgreSQL supprime physiquement les champs légaux (`kyb_rc`, `kyb_nif`, `kyb_statut_cnrc`, `kyb_date_radiation`, statut d'audit des factures) et vos tiers perdent leur traçabilité légale.  
> **La mise à jour in-place via le bouton « Mettre à jour maintenant » préserve 100% de vos données de conformité, vos colonnes fiscales, vos clés API, vos notes Chatter et vos historiques d'audit.**

* **Gestion des Droits d'Écriture :** Le connecteur vérifie préalablement que le répertoire d'addons est accessible en écriture (`os.access(module_path, os.W_OK)`). Si le module est déployé sur un système de fichiers monté en lecture seule stricte (ex: grappe Kubernetes immuable), le bouton informe explicitement l'administrateur de procéder à la mise à jour via son pipeline Git ou DevOps.

#### E. Télémétrie Flotte & Souveraineté Numérique (Loi 18-07 & Loi 25-11)
À chaque vérification de version ou battement de cœur de la tâche cron, le connecteur transmet un diagnostic de santé d'instance vers `POST /api/v1/client/telemetry` :
* **Données Techniques Transmises (Diagnostic Flotte) :**
  * Version du connecteur KYB et version du socle Odoo (e.g. `2.0.0`, `20.0`).
  * Type d'édition (Community ou Enterprise), version Python et système d'exploitation hôte.
  * Identifiant UUID anonymisé de la base de données (`database.uuid`).
  * Compteurs numériques agrégés : nombre total de partenaires, partenaires vérifiés, partenaires actifs, partenaires radiés, factures auditées, factures conformes, factures bloquées.
  * Indicateurs de configuration active : politique de validation choisie (`strict_block` ou `soft_warn`), politique des doublons NIF (`warn` ou `block`).
* **ENGAGEMENT DE CONFIDENTIALITÉ ABSOLUE (ZÉRO PII) :**  
  Conformément à la **Loi 18-07** (protection des données à caractère personnel) et à la **Loi 25-11** (souveraineté des données) :
  * ❌ **AUCUN** nom d'entreprise cliente ou fournisseur n'est transmis.
  * ❌ **AUCUN** nom de contact, dirigeant ou particulier n'est collecté.
  * ❌ **AUCUN** montant financier, chiffre d'affaires, ligne d'article ou prix n'est accessible.
  * ❌ **AUCUN** numéro de facture ou libellé comptable ne quitte votre base de données.
* **Résidence 100% Algérienne :** Toutes les données de diagnostic transitent et sont traitées exclusivement sur les serveurs souverains opérés au Datacenter national d'Algérie Télécom (Cloud Souverain). Aucun appel vers des régies publicitaires, traceurs ou services tiers étrangers (CDNs, Google Analytics, serveurs offshore) n'est effectué.

#### F. Exigences Réseau & Pare-Feu d'Entreprise
Pour les entreprises opérant derrière un pare-feu d'entreprise (Corporate Firewall / Proxy) :
* **Flux sortant requis :** Port HTTPS **443** vers le nom de domaine officiel `kyb.digidevagency.dz`.
* **Aucune dépendance externe :** Le module n'effectue aucun appel vers `github.com`, `pypi.org`, `npmjs.com` ou des CDNs publics. Tout est servi directement par la passerelle nationale KYB.

---

## 3. Saisie Automatique & Enrichissement des Entreprises (Personnes Morales)

Lors de la création d'un nouveau partenaire (**Contacts → Nouveau**) :

### Étape 1 : Recherche en temps réel par nom d'entreprise (0 Crédit / Inclus)
1. Cochez la case **Société** (`is_company = True`).
2. Saisissez le début de la dénomination commerciale (ex: `CEVITAL`).
3. La liste déroulante intelligente interroge instantanément l'index souverain en direct (temps de réponse <10ms) et présente les entités correspondantes avec leur siège social.
   * **Gratuité de la recherche prédictive :** En version 2.0.0, l'auto-complétion exploratoire par nom est incluse à **0 unité débitée** de votre abonnement (recherches illimitées pour vos équipes commerciales et achats).

![Recherche en direct CEVITAL avec 9 filiales](screenshots/01_autocomplete_cevital.png)
*Figure 2 : Auto-complétion interactive affichant en temps réel les entités légales officielles.*

### Étape 2 : Sélection et enrichissement légal certifié (1 Unité avec Garantie Remboursement)
Dès que vous cliquez sur l'entité retenue (ex: *CEVITAL MENERALS*) :
* **Raison sociale & Forme juridique :** Importées avec précision (`SPA`, `SARL`, `EURL`...).
* **Identifiants légaux :** Le **NIF (15 chiffres)**, le **RC officiel** normalisé Décret 05-468 (`08/00-0979866B19`), et le **NIS** sont insérés.
* **Gouvernance & Capital :** Le capital social déclaré (`5 450 000 000 DA`) et l'identité du Représentant Légal (`RABRAB MALIK`) sont renseignés.
* **Activités économiques :** L'activité principale dominante et l'ensemble des codes NAE officiels sont indexés.
* **Adresse du siège social :** Rue et Wilaya sont automatiquement affectées.
* **Statut officiel :** Le badge vert **🟢 Actif** signale l'état d'activité répertorié.
* **Fil d'audit (Chatter) :** Une note institutionnelle datée et horodatée consigne la consultation pour assurer la traçabilité.
* **Tarification & Garantie :** Cette opération de certification officielle déduit **1 crédit** de votre solde central d'entreprise. Si l'entité n'est pas trouvée ou si une indisponibilité temporaire du portail public survient, un remboursement automatique immédiat (`issueSingleRefund`) est recrédité à votre compte sans délai.

![Fiche Entreprise enrichie CEVITAL MENERALS](screenshots/02_corporate_sheet_pm.png)
*Figure 3 : Fiche contact enrichie avec ses données de gouvernance, son statut Actif et son historique d'audit.*

---

## 4. Enregistrement des Commerçants & Artisans (Personnes Physiques)

Pour les personnes physiques (entreprises individuelles, commerçants de détail, artisans), la réglementation relative aux données personnelles (Loi 18-07) encadre la recherche nominale. Le connecteur permet leur identification directe par leurs identifiants officiels.

### Étape 1 : Saisie de l'identifiant individuel (NIF ou RC Catégorie A/C)
1. Créez un contact et laissez l'option **Individu** sélectionnée (`is_company = False`).
2. Saisissez son **NIF individuel à 15 chiffres** (commençant par le chiffre `1`) ou son **Numéro RC Catégorie A ou C** (ex: `26A16208703` ou clé de test `000021623880453`).

### Étape 2 : Résolution et enrichissement complet de la fiche Personne Physique
Dès la saisie ou au clic sur **Vérifier Fiche KYB**, le connecteur résout immédiatement le profil :
* **Forme juridique :** Qualifiée automatiquement en `"Personne Physique"`.
* **Registre de Commerce normalisé :** Formaté au standard officiel Décret 05-468 (`26/00-16208703A26`).
* **Capital social adapté :** Qualifié en `"N/A (Patrimoine Individuel)"` (absence de capital social statutaire distinct).
* **Gouvernance & Titularité :** Titulaire exploitant renseigné (`BENALI SOFIANE (Titulaire)`).
* **Activités économiques NAE :** Activité principale (`Commerce de détail d'ordinateurs...`) et activités secondaires répertoriées.
* **Statut officiel & Traçabilité :** Badge vert **🟢 Actif** affiché et carte institutionnelle détaillée consignée au fil Chatter.

![Fiche Commerçant Individuel Personne Physique](screenshots/03_individual_merchant_pp.png)
*Figure 4 : Fiche Personne Physique enrichie (BENALI SOFIANE) avec son RC Catégorie A, son capital individuel N/A et son fil d'audit Chatter complet.*

---

## 5. Prévention Proactive des Doublons Fiscaux

En Algérie, le **NIF** est un identifiant fiscal national unique. La multiplication accidentelle de fiches pour un même tiers engendre des décalages de comptabilité auxiliaire et fausse l'état 104 des clients. Le connecteur KYB propose trois niveaux de politique configurables :

### A. Comportement selon la Politique Sélectionnée
* **1. Mode Avertissement (Par défaut) :**
  * Dès qu'un NIF existant est saisi, une bannière d'alerte contextuelle apparaît en haut de fiche (`Doublons potentiels : CEVITAL MENERALS (Même TIN)`).
  * Une boîte de dialogue explicite s'affiche avec le nom, l'identifiant interne (#ID) du contact existant et la conduite à tenir. L'utilisateur peut choisir de consulter le contact existant ou poursuivre si nécessaire.
* **2. Mode Blocage Strict :**
  * Empêche formellement l'enregistrement ou la sauvegarde d'un contact comportant un NIF déjà attribué (`UserError: Le NIF ... est déjà attribué au partenaire ... En vertu de la politique de non-duplication fiscale, l'enregistrement est bloqué.`).
* **3. Mode Ignorer :**
  * Désactive la vérification pour les structures multi-établissements ayant des fiches distinctes avec un NIF commun.

### B. Procédure de Consolidation (Fusion de Contacts)
Si des doublons existent déjà dans votre base de données :
1. Sélectionnez les deux fiches dans la liste des contacts.
2. Cliquez sur **Action → Fusionner**.
3. Validez la fusion : l'intégralité des données KYB (RC normalisé, NIF, statut, historique Chatter) est conservée sans aucune perte d'informations.

![Alerte de doublon fiscal et fenêtre de dialogue](screenshots/04_duplicate_nif_prevention.png)
*Figure 5 : Alerte native de prévention des doublons fiscaux lors de la saisie d'un NIF existant.*

---

## 6. Bouclier Fiscal des Achats : Audit Temporel & Sécurisation TVA/IBS

En droit fiscal algérien (**Articles 169 & 176 du CIDTA** et **Article 30 du CTCA**), les achats de biens et prestations de services contractés auprès d'une entreprise radiée des registres officiels ne sont pas déductibles de l'IBS et de la TVA. En cas de contrôle fiscal, ces montants s'exposent à un rejet comptable assorti de pénalités de retard.

> [!IMPORTANT]
> **Enjeu de Sécurité Comptable :** L'éligibilité fiscale d'une charge s'apprécie **à la date exacte d'émission de la facture**. Même si un fournisseur était en règle lors de la conclusion initiale d'un contrat, une facture émise après sa date de radiation expose l'entreprise à une réintégration fiscale. KYB intègre un dispositif d'alerte en 3 paliers pour signaler ce risque avant règlement.

### Cycle de Sécurisation en 3 Paliers

| Palier de Contrôle | Déclencheur & Mécanisme | Action du Système | Utilité Opérationnelle |
| :---: | :--- | :--- | :--- |
| **Palier 1**<br>*(Prévention Immédiate)* | **À la saisie du fournisseur & de la date :**<br>Contrôle chronologique instantané (*Onchange*). | **Alerte visuelle immédiate :** Affichage en tête de facture d'une bannière rouge d'avertissement et badge `🔴 Non Conforme`. | **Gain de temps :** L'anomalie est signalée avant même la saisie des montants et des lignes de facture. |
| **Palier 2**<br>*(Sécurité de Validation)* | **Au clic sur « Confirmer » :**<br>Contrôle de fraîcheur JIT (24h) et actualisation silencieuse sur les portails publics. | **Application de la politique configurée :**<br>• *Mode Strict :* Interruption de validation (`UserError`) avec motivation.<br>• *Mode Avertissement :* Validation avec note explicite au Chatter. | **Aide à la décision :** Évite la validation par inadvertance d'une facture émise par un tiers non actif au registre. |
| **Palier 3**<br>*(Vérification Périodique)* | **Avant clôture mensuelle (18 du mois) :**<br>Balayage automatique des pièces d'achat de la période. | **Rapport de synthèse consolidé :** Détection des radiations intervenues au cours du mois écoulé. | **Sérénité de déclaration :** Permet à l'équipe comptable d'assainir ses écritures avant l'échéance de télédéclaration (G50). |

![Bannière de rejet fiscal sur fournisseur radié](screenshots/06_temporal_invoice_audit_bill.png)
*Figure 6 : Bannière d'alerte temporelle sur une facture émise postérieurement à la date de radiation du fournisseur.*

### Tableau de bord de conformité des factures d'achat :
Dans la liste de vos factures d'achat (**Facturation → Fournisseurs → Factures**) :
* La colonne **Conformité Fiscale KYB** permet de visualiser en un coup d'œil le statut légal de chaque facture :
  * **🟢 Conforme (Actif) :** Fournisseur en règle, charge et TVA éligibles à déduction.
  * **🔴 Non Conforme (Fournisseur Radié) :** Risque de rejet fiscal signalé, examen comptable recommandé.

![Vue liste des factures d'achat avec statuts de conformité](screenshots/07_vendor_bills_compliance_tree.png)
*Figure 7 : Vue synthétique des factures fournisseurs avec indicateurs visuels de conformité fiscale en temps réel.*

---

## 7. Audit de Fin de Mois & Préparation de la Déclaration G50

Pour sécuriser l'envoi mensuel de votre déclaration fiscale (G50) :
1. Accédez à **Conforme KYB → ⚡ Audit Fin de Mois (G50)**.
2. Le système passe en revue l'ensemble des factures d'achat comptabilisées sur la période en cours.
3. Tout fournisseur ayant fait l'objet d'une radiation récente est isolé avant la clôture, permettant d'assainir vos écritures avant dépôt de la déclaration.

---

## 8. Questions Fréquentes (FAQ)

### Comment renouveler ou modifier ma clé d'API ?
Rendez-vous sur [kyb.digidevagency.dz](https://kyb.digidevagency.dz) dans la section **Clés API**. Une fois une nouvelle clé générée, collez-la simplement dans **Paramètres → KYB Compliance** dans Odoo et cliquez sur **Enregistrer**.

### Que faire si une entreprise n'apparaît pas dans l'auto-complétion ?
Si la dénomination commerciale est très récente ou orthographiée de manière spécifique, saisissez directement son **NIF à 15 chiffres** ou son **Numéro RC**. Le connecteur interrogera directement le registre central.

### Comment s'effectuent les montées de version (v2.0.0) ?
Grâce au moteur d'upgrade autonome intégré à la version 2.0.0, toute mise à jour ou patch réglementaire est déployé en 1 clic directement dans **Paramètres → KYB Compliance** via le bouton **Mettre à jour maintenant (1-Clic)**, sans aucune intervention en ligne de commande ni interruption de service.

### Y a-t-il un risque de perte de données lors de la mise à jour in-place ?
**Absolument aucun.** La mise à jour in-place exécute le rechargement natif de l'ORM Odoo (`button_immediate_upgrade`). Elle préserve à 100% l'intégralité de vos colonnes fiscales (`kyb_rc`, `kyb_nif`, `kyb_statut_cnrc`), l'ensemble des historiques d'audit dans les fils de discussion (Chatter), ainsi que vos clés d'API et configurations.

### Pourquoi ne faut-il JAMAIS cliquer sur « Désinstaller » sur le module ?
Dans l'architecture PostgreSQL d'Odoo, une désinstallation supprime physiquement les colonnes de la base de données associées au module. Cliquer sur *Désinstaller* détruirait donc vos identifiants NIF, RC et dates de radiation stockés. Si vous souhaitez mettre à jour ou corriger le module, utilisez **toujours** le bouton **Mettre à jour maintenant (1-Clic)** ou la fonction de mise à niveau native d'Odoo.

### Quelles sont les exigences réseau et pare-feu d'entreprise ?
Le connecteur nécessite uniquement un flux sortant HTTPS standard (port **443**) vers l'adresse souveraine `kyb.digidevagency.dz`. Aucun accès à des services tiers étrangers (GitHub, NPM, PyPI, Google) n'est nécessaire. Si votre serveur Odoo passe par un proxy d'entreprise, assurez-vous que `kyb.digidevagency.dz` est autorisé.

### La télémétrie de version présente-t-elle un risque pour les données confidentielles ?
**Aucun.** La télémétrie est strictement conforme aux **Lois 18-07 et 25-11**. Elle ne transmet que des données techniques d'intégrité (version d'Odoo, compteurs numériques globaux de fiches). Aucun nom de société, de dirigeant, de facture ou montant financier ne quitte votre base de données.

### L'auto-complétion prédictive consomme-t-elle des crédits ?
Non. En version 2.0.0, l'auto-complétion prédictive par nom d'entreprise ou marque est incluse à **0 unité** (recherche de suggestions en direct, cache <10ms). Seule la certification officielle et l'enrichissement complet de la fiche légale déduisent une unité de votre solde. Si une recherche officielle ne donne aucun résultat ou si le portail gouvernemental est en maintenance, un remboursement automatique (`issueSingleRefund`) est crédité immédiatement.

### Comment tester le module gratuitement avant mise en production (Sandbox) ?
Vous pouvez utiliser la clé de bac à sable gratuite `sk_test_kyb_sandbox_key_001` ou vos clés de production avec les identifiants déterministes Sandbox (NIFs commençant par `0000...` e.g. `000000000000001` pour une société active ou `000000000000002` pour une société radiée). Ces requêtes de test ne consomment aucun crédit.

### Pourquoi le numéro d'Article d'Imposition (Rôle) n'est-il pas rempli automatiquement ?
En vertu de l'**Article 114 du Code des Procédures Fiscales (CPF)**, le Numéro de Rôle relève du secret fiscal et n'est pas un identifiant public. Il figure obligatoirement sur les factures imprimées de vos fournisseurs (Décret 05-468) et doit être renseigné lors du premier traitement de facture. Une fois saisi, KYB le conserve et l'associe définitivement à la fiche tiers.

---

## Support & Assistance Technique
* **Portail officiel :** [https://kyb.digidevagency.dz](https://kyb.digidevagency.dz)  
* **Documentation & API :** [https://kyb.digidevagency.dz/docs](https://kyb.digidevagency.dz/docs)  
* **Support Client :** support@kyb.digidevagency.dz  
