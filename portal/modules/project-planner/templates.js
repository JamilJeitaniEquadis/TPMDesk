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
const ms = (name, r, a, c, i, d) => t(name, r, a, c, i, d, 1, { milestone: true });

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
