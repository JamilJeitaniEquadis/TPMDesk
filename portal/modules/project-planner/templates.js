/* Project planner: the standard roles and the project templates.
   Each template is a list of phases; each task has its RACI by role code and its timing in days
   from the project start (d = first day, n = length in days). Edit here to change every new plan. */
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
  {
    id: 'interface', name: 'Data integration interface', note: 'Product / logistics or photos interface with a client',
    phases: [
      { name: 'Preparation', tasks: [
        ms('Kick-off meeting', 'EPM, CPM', 'EPM', 'CPM, ECL', 'EKAM', 0),
        t('Kick-off technical meeting', 'EPM, CPM', 'EPM', 'CPM', 'EFM, EKAM', 2, 1),
        t('Documentation pack sent', 'EPM', 'EPM', '', 'CPM', 3, 2),
      ] },
      { name: 'Interface', tasks: [
        t('Documentation analysis', 'CPM', 'EPM', 'CPM', 'EKAM', 5, 5),
        t('Client conception', 'CPM', 'CPM', 'EPM', '', 10, 5),
        t('Client development', 'CPM', 'EPM', 'CPM', 'EFM, EKAM', 15, 10),
        t('Equadis development', 'EFM', 'EPM', 'EKAM', 'CPM', 15, 10),
        t('Technical tests', 'EFM', 'EPM', 'CPM', 'ETS, ECS', 25, 5),
        t('Functional tests', 'EPM', 'EPM', 'CPM', 'EFM, EKAM, ECS, ETS', 30, 5),
        ms('Deployment on production', 'EPM', 'EPM', 'CPM', 'EFM, EKAM, ECS, ETS, ECL', 35),
      ] },
      { name: 'Production', tasks: [
        t('Users training', 'EKAM', 'ECS', 'CPM', 'EPM', 36, 2),
        t('Hypercare', 'ETS', 'EPM', 'CPM', 'EKAM', 36, 10),
      ] },
      { name: 'Governance', tasks: [
        t('Weekly project committee call', 'EPM', 'EPM', 'CPM', 'EKAM', 0, 46),
        t('Steering committee call (every two weeks)', 'EPM', 'EPM', 'CPM, ECL', 'EKAM', 0, 46),
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
