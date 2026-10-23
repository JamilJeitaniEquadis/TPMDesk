/* Project planner: the standard roles and the project templates.
   Each template is a list of phases; each task has its RACI by role code and its timing in days
   from the project start (d = first day, n = length in days; working days when the template says workdays).
   A name can be [English, French]: the plan's Excel language picks one. Edit here to change every new plan. */
window.PLANNER_ROLES = [
  { code: 'CPM',   title: 'Client project manager',               side: 'Client'  },
  { code: 'EPM',   title: 'Equadis project manager',              side: 'Equadis' },
  { code: 'ETS',   title: 'Equadis technical support team leader', side: 'Equadis' },
  { code: 'EFM',   title: 'Equadis flow manager',                 side: 'Equadis' },
  { code: 'EDEV',  title: 'Equadis development team',             side: 'Equadis' },
  { code: 'EQA',   title: 'Equadis QA team',                      side: 'Equadis' },
  { code: 'ERSSI', title: 'Equadis RSSI (security)',              side: 'Equadis' },
  { code: 'ECS',   title: 'Equadis customer support team leader', side: 'Equadis' },
  { code: 'EKAM',  title: 'Equadis key account manager',          side: 'Equadis' },
  { code: 'ECL',   title: 'Equadis C-level',                      side: 'Equadis' },
];

/* t(name, R, A, C, I, d, n) */
const t = (name, r, a, c, i, d, n, extra) => Object.assign({ name, r, a, c, i, d, n }, extra || {});
const ms = (name, r, a, c, i, d, extra) => t(name, r, a, c, i, d, 1, Object.assign({ milestone: true }, extra || {}));

window.PLANNER_TEMPLATES = [
  { id: 'blank', name: 'Blank plan', note: 'One empty phase', phases: [{ name: 'Phase 1', tasks: [] }] },
  /* Data interfaces, from the team's retroplannings (MS Project): durations in WORKING days, names in [English, French].
     Products (~47 days), visuals (~27 days), or both in sequence (~63 days). */
  {
    id: 'product', name: 'Product interface', note: 'Client product data flow into GAIA, about 10 weeks', workdays: true,
    phases: [
      { name: ['Kick-off', 'Kick-off'], tasks: [
        ms(['Kick-off meeting', 'Réunion de kick-off'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, EFM', 0),
      ] },
      { name: ['Product interface', 'Interface produits'], tasks: [
        t(['Documentation analysis', 'Analyse de la documentation'], 'CPM', 'EPM', 'EFM', 'EKAM', 1, 2),
        t(['Data workshops and field mapping (Excel file)', 'Workshops données et mapping des champs (fichier Excel)'], 'EPM, CPM', 'EPM', 'EFM', 'EKAM', 3, 10),
        t(['Technical pre-call', 'Pré-call technique'], 'EFM, CPM', 'EPM', '', 'EKAM', 13, 1),
        t(['Product flow development (Equadis XML format)', 'Développement du flux produits (format XML Equadis)'], 'CPM', 'CPM', 'EFM', 'EPM', 14, 20),
        t(['Technical test', 'Test technique'], 'EFM, CPM', 'EPM', '', 'ETS', 34, 5),
        t(['Business validation', 'Validation métier'], 'CPM, EPM', 'CPM', 'EFM', 'EKAM', 39, 5),
      ] },
      { name: ['Go-live preparation', 'Préparation du go-live'], tasks: [
        t(['Production deployment', 'Déploiement en production'], 'EFM', 'EPM', 'CPM', 'ETS, ECS', 44, 2),
        t(['Users training', 'Formation des utilisateurs'], 'EKAM', 'ECS', 'CPM', 'EPM', 46, 1),
        ms(['Go-live', 'Go-live'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, ECS, ETS, ECL', 47),
      ] },
    ],
  },
  {
    id: 'visuals', name: 'Visuals interface', note: 'Client photos and documents flow into GAIA, about 6 weeks', workdays: true,
    phases: [
      { name: ['Kick-off', 'Kick-off'], tasks: [
        ms(['Kick-off meeting', 'Réunion de kick-off'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, EFM', 0),
      ] },
      { name: ['Visuals interface', 'Interface visuels'], tasks: [
        t(['Documentation analysis', 'Analyse de la documentation'], 'CPM', 'EPM', 'EFM', 'EKAM', 1, 1),
        t(['Visuals field mapping (Excel file)', 'Mapping des champs visuels (fichier Excel)'], 'CPM, EPM', 'EPM', 'EFM', '', 2, 5),
        t(['Technical pre-call', 'Pré-call technique'], 'EFM, CPM', 'EPM', '', 'EKAM', 7, 1),
        t(['Visuals flow development (Equadis XML format)', 'Développement du flux visuels (format XML Equadis)'], 'CPM', 'CPM', 'EFM', 'EPM', 8, 10),
        t(['Technical test', 'Test technique'], 'EFM, CPM', 'EPM', '', 'ETS', 18, 3),
        t(['Business validation', 'Validation métier'], 'CPM, EPM', 'CPM', 'EFM', 'EKAM', 21, 2),
      ] },
      { name: ['Go-live preparation', 'Préparation du go-live'], tasks: [
        t(['Production deployment', 'Déploiement en production'], 'EFM', 'EPM', 'CPM', 'ETS, ECS', 23, 2),
        t(['Users training', 'Formation des utilisateurs'], 'EKAM', 'ECS', 'CPM', 'EPM', 25, 1),
        ms(['Go-live', 'Go-live'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, ECS, ETS, ECL', 26),
      ] },
    ],
  },
  {
    id: 'product-visuals', name: 'Product and visuals interfaces', note: 'Products first, then visuals, one go-live, about 13 weeks', workdays: true,
    phases: [
      { name: ['Kick-off', 'Kick-off'], tasks: [
        ms(['Kick-off meeting', 'Réunion de kick-off'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, EFM', 0),
      ] },
      { name: ['Product interface', 'Interface produits'], tasks: [
        t(['Documentation analysis', 'Analyse de la documentation'], 'CPM', 'EPM', 'EFM', 'EKAM', 1, 2),
        t(['Data workshops: final data model', 'Workshops analyse des données : modèle de données final'], 'EPM, CPM', 'EPM', 'EFM', 'EKAM', 3, 10),
        t(['Technical pre-call', 'Pré-call technique'], 'EFM, CPM', 'EPM', '', 'EKAM', 13, 1),
        t(['Product flow development (Equadis XML format)', 'Développement du flux produits (format XML Equadis)'], 'CPM', 'CPM', 'EFM', 'EPM', 14, 20),
        t(['Technical test', 'Test technique'], 'EFM, CPM', 'EPM', '', 'ETS', 34, 5),
        t(['Business validation', 'Validation métier'], 'CPM, EPM', 'CPM', 'EFM', 'EKAM', 39, 5),
      ] },
      { name: ['Visuals interface', 'Interface visuels'], tasks: [
        t(['Documentation analysis', 'Analyse de la documentation'], 'CPM', 'EPM', 'EFM', 'EKAM', 44, 1),
        t(['Technical pre-call', 'Pré-call technique'], 'EFM, CPM', 'EPM', '', 'EKAM', 45, 1),
        t(['Visuals flow development (Equadis XML format)', 'Développement du flux visuels (format XML Equadis)'], 'CPM', 'CPM', 'EFM', 'EPM', 46, 10),
        t(['Technical test', 'Test technique'], 'EFM, CPM', 'EPM', '', 'ETS', 56, 2),
        t(['Business validation', 'Validation métier'], 'CPM, EPM', 'CPM', 'EFM', 'EKAM', 58, 2),
      ] },
      { name: ['Go-live preparation', 'Préparation du go-live'], tasks: [
        t(['Production deployment', 'Déploiement en production'], 'EFM', 'EPM', 'CPM', 'ETS, ECS', 60, 1),
        t(['Users training', 'Formation des utilisateurs'], 'EKAM', 'ECS', 'CPM', 'EPM', 61, 1),
        ms(['Go-live', 'Go-live'], 'EPM, CPM', 'EPM', 'CPM', 'EKAM, ECS, ETS, ECL', 62),
      ] },
    ],
  },
  /* DSA proof of concept, from the team's POC plan: three sheets (Scope, Tracker, Gantt), working days.
     scope.fields: [English, French, hint]; scope.tables: columns [English, French]; a task's note is its detail. */
  {
    id: 'dsa-poc', name: 'DSA POC', note: 'Proof of concept: scope, tracker and timeline, about 7 weeks', workdays: true,
    sheets: ['scope', 'tracker', 'gantt'],
    scope: {
      fields: [
        ['Objective', 'Objectif', 'Monitor N client products and their competitors on N retailers in N markets'],
        ['Ready date', 'Date de mise à disposition', 'All data loaded and tested'],
        ['POC period', 'Période du POC', 'Start - end (3 weeks)'],
        ['Markets', 'Marchés', 'Countries'],
        ['Client products', 'Produits client', 'N SKUs (max. 15), by category'],
        ['Competitors', 'Concurrents', '1 competitor SKU per client SKU'],
        ['Retailers', 'Distributeurs', 'N retailers, by country'],
        ['Client users', 'Utilisateurs client', 'N users (max. 10)'],
        ['User language', 'Langue des utilisateurs', 'English, French…'],
        ['Equadis owner', 'Responsable Equadis', 'Project manager'],
      ],
      tables: [
        { name: ['Retailers', 'Distributeurs'], cols: [['Retailer', 'Distributeur'], ['Country', 'Pays'], ['Website', 'Site'], ['DSA features', 'Fonctions DSA']] },
        { name: ['Products', 'Produits'], cols: [['Client GTIN', 'GTIN client'], ['Category', 'Catégorie'], ['Client product', 'Produit client'], ['Competitor product', 'Produit concurrent'], ['Competitor GTIN', 'GTIN concurrent']] },
      ],
    },
    phases: [
      { name: ['1. Data preparation', '1. Préparation des données'], tasks: [
        t(['Export GAIA data for the POC products and load them in e-agora (bulk update)', 'Exporter les données GAIA des produits du POC et les intégrer dans e-agora (mise à jour en masse)'], 'EPM', 'EPM', '', '', 0, 2, { note: ['GAIA data export → e-agora bulk update', 'Export GAIA → mise à jour en masse e-agora'] }),
        t(['Add the retailer connectors to the client account and subscribe the products', 'Ajouter les connecteurs distributeurs au compte client et abonner les produits'], 'EPM', 'EPM', '', '', 1, 2, { note: ['One connector per retailer', 'Un connecteur par distributeur'] }),
        t(['Check that e-agora data matches GAIA data', 'Vérifier que les données e-agora correspondent à GAIA'], 'EPM', 'EPM', '', '', 1, 2),
        t(['Add the client recommended prices (SRP) for the target markets', 'Ajouter les prix conseillés (SRP) du client pour les marchés cibles'], 'EPM', 'EPM', 'CPM', '', 2, 1),
        t(['Support tickets: clean the retailers and products already in the account', 'Tickets support : nettoyer les distributeurs et produits déjà présents sur le compte'], 'EPM', 'EPM', '', 'ETS', 2, 1),
        t(['Prepare the assortment file and insert it in SQL', 'Préparer le fichier d’assortiment et l’insérer en SQL'], 'EPM', 'EPM', '', 'ETS', 2, 2),
        t(['Prepare the keywords file and insert it in SQL', 'Préparer le fichier de mots-clés et l’insérer en SQL'], 'EPM', 'EPM', '', 'ETS', 2, 2),
        t(['Prepare the competitors file and insert it in SQL', 'Préparer le fichier des concurrents et l’insérer en SQL'], 'EPM', 'EPM', '', 'ETS', 2, 2),
        t(['Run the skill, complete the product assortment and send it to the data provider', 'Lancer le skill, compléter l’assortiment produits et l’envoyer au fournisseur de données'], 'ETS', 'EPM', '', '', 3, 7),
        t(['Complete the keywords and send them to the data provider', 'Compléter les mots-clés et les envoyer au fournisseur de données'], 'ETS', 'EPM', '', '', 3, 7),
        t(['Run the skill, complete the competitors file and send it to the data provider', 'Lancer le skill, compléter le fichier des concurrents et l’envoyer au fournisseur de données'], 'ETS', 'EPM', '', '', 3, 7),
      ] },
      { name: ['2. Loading and configuration', '2. Chargement et configuration'], tasks: [
        t(['Integrate the product assortment in e-agora', 'Intégrer l’assortiment produits dans e-agora'], 'EPM', 'EPM', '', '', 9, 2, { note: ['Subscriptions screen', 'Écran des abonnements'] }),
        t(['Integrate the competitor assortment in e-agora', 'Intégrer l’assortiment concurrents dans e-agora'], 'EPM', 'EPM', '', '', 9, 2, { note: ['Competitors screen', 'Écran des concurrents'] }),
        t(['Create the client users', 'Créer les utilisateurs client'], 'EPM', 'EPM', '', 'CPM', 10, 2),
        t(['Set up the POC features', 'Paramétrer les fonctionnalités du POC'], 'EPM', 'EPM', 'EDEV', '', 10, 3),
      ] },
      { name: ['3. Dry run and readiness', '3. Test à blanc et mise à disposition'], tasks: [
        t(['First collection run on the retailers', 'Première collecte sur les distributeurs'], 'EPM', 'EPM', 'EDEV', '', 10, 3),
        t(['Check the match rate per retailer', 'Vérifier le taux de correspondance par distributeur'], 'EPM', 'EPM', 'ETS', '', 11, 3, { note: ['Client and competitor products found / expected', 'Produits client et concurrents trouvés / attendus'] }),
        t(['Data fixes', 'Corrections des données'], 'EPM', 'EPM', 'ETS', '', 12, 3),
        ms(['Everything ready', 'Tout est prêt'], 'EPM', 'EPM', '', 'CPM, EKAM', 14),
      ] },
      { name: ['4. Client onboarding', '4. Onboarding client'], tasks: [
        t(['Send the logins to the client users', 'Envoyer les accès aux utilisateurs client'], 'EPM', 'EPM', '', 'CPM', 15, 2),
        t(['Onboarding session with the client', 'Session d’onboarding avec le client'], 'EPM', 'EPM', 'CPM', 'EKAM', 17, 2),
        t(['Success criteria and weekly check-in slot', 'Critères de succès et créneau du point hebdomadaire'], 'EPM, CPM', 'EPM', '', 'EKAM', 18, 2),
      ] },
      { name: ['5. POC run', '5. Déroulement du POC'], tasks: [
        ms(['POC kick-off', 'Lancement du POC'], 'EPM', 'EPM', 'CPM', 'EKAM', 20),
        t(['Daily collection monitoring', 'Suivi quotidien des collectes'], 'EPM', 'EPM', '', '', 20, 15, { note: ['Every day, all retailers', 'Chaque jour, tous les distributeurs'] }),
        t(['Weekly check-in 1 with the client', 'Point hebdomadaire 1 avec le client'], 'EPM', 'EPM', 'CPM', '', 24, 1, { note: ['Coverage, issues, first findings', 'Couverture, problèmes, premiers constats'] }),
        t(['Weekly check-in 2 with the client', 'Point hebdomadaire 2 avec le client'], 'EPM', 'EPM', 'CPM', '', 29, 1, { note: ['Coverage, issues, first findings', 'Couverture, problèmes, premiers constats'] }),
        t(['POC results report', 'Rapport de résultats du POC'], 'EPM', 'EPM', '', 'EKAM', 30, 4, { note: ['Per retailer and per feature', 'Par distributeur et par fonctionnalité'] }),
        ms(['Closing meeting', 'Réunion de clôture'], 'EPM', 'EPM', 'CPM', 'EKAM, ECL', 34, { note: ['Results and next steps', 'Résultats et prochaines étapes'] }),
      ] },
      { name: ['6. Follow-up', '6. Suivi'], tasks: [
        t(['Weekly tracker review', 'Revue hebdomadaire du tracker'], 'EPM', 'EPM', '', '', 0, 35, { note: ['Every Monday', 'Chaque lundi'] }),
      ] },
    ],
  },
  {
    id: 'sso', name: 'SSO (OAuth)', note: 'Single sign-on between the client and Equadis',
    phases: [
      { name: 'Preparation', tasks: [
        ms('Kick-off meeting', 'EPM', 'EPM', 'CPM, ERSSI', 'EKAM', 0),
        t('Client identity provider values (Prod and Test)', 'CPM', 'CPM', 'ERSSI', 'EPM', 1, 7),
      ] },
      { name: 'SSO via OAuth', tasks: [
        t('Equadis development', 'EPM, ERSSI', 'EPM', 'CPM', 'EKAM', 8, 5),
        t('Technical tests', 'EPM, ERSSI', 'EPM', 'CPM', '', 13, 3),
        t('Functional tests', 'EPM, ERSSI', 'EPM', 'CPM', '', 16, 3),
        ms('Deployment on production', 'EPM, ERSSI', 'EPM', 'CPM', 'EFM, ECS, ETS', 19),
      ] },
    ],
  },
  {
    id: 'dsa', name: 'DSA onboarding', note: 'E-retailer sites, assortment, scraping and delivery',
    phases: [
      { name: 'Preparation', tasks: [
        ms('Kick-off meeting', 'EPM', 'EPM', 'CPM', 'EKAM', 0),
        t('List of sites', 'CPM', 'CPM', 'EPM', 'ETS', 1, 5),
        t('Products list and keywords', 'CPM', 'CPM', 'EPM', 'ETS', 1, 5),
      ] },
      { name: 'Wave 1 - sites onboarding', tasks: [
        t('Site discovery (new sites)', 'ETS', 'EPM', '', 'CPM', 6, 5),
        t('Products identification and URLs', 'ETS', 'EPM', '', '', 6, 10),
        t('Product assortment configuration', 'EDEV', 'EPM', 'ETS', '', 11, 5),
        t('Scraping', 'EDEV', 'EPM', 'ETS', '', 16, 7),
        t('Results testing and validation', 'ETS', 'EPM', 'EQA', 'CPM', 23, 4),
        ms('Sites delivery', 'EDEV', 'EPM', 'ETS', 'CPM, EKAM', 27),
      ] },
      { name: 'Follow-up', tasks: [
        t('Coverage report', 'ETS', 'EPM', '', 'CPM', 28, 5),
        t('Client feedback and fixes', 'EDEV', 'EPM', 'CPM', 'EKAM', 28, 10),
      ] },
    ],
  },
  {
    id: 'migration', name: 'Catalogue migration', note: 'Supplier data moved from another pool into GAIA',
    phases: [
      { name: 'Preparation', tasks: [
        ms('Kick-off meeting', 'EPM', 'EPM', 'CPM', 'EKAM', 0),
        t('Exports received from the source pool', 'CPM', 'CPM', 'EPM', '', 1, 5),
        t('Mapping to the Equadis format', 'EPM', 'EPM', 'EFM', 'CPM', 4, 5),
      ] },
      { name: 'Integration', tasks: [
        t('Integration interface setup', 'EPM', 'EPM', 'EFM', '', 9, 2),
        t('Files converted and integrated by supplier', 'EPM', 'EPM', 'EFM', 'CPM', 11, 10),
        t('Integration errors fixed', 'EPM', 'EPM', 'EFM', 'CPM', 14, 10),
      ] },
      { name: 'Acceptance', tasks: [
        t('Client checks on the platform', 'CPM', 'CPM', 'EPM', 'EKAM', 24, 5),
        ms('Migration closed', 'EPM', 'EPM', 'CPM', 'EKAM, ECL', 29),
      ] },
    ],
  },
];
