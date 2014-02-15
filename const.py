
ITEM_L_STATUS = (
('active', 1),
('customized', 2),
('discontinued', 3),
('display/sample', 4),
('inactive', 5),
('internal use', 6),
('obsolete', 7),
('special order', 8)
)

ITEM_D_STATUS = dict(ITEM_L_STATUS)


ITEM_L_DEPT = (
('apparel', 'other'),
('asianware', 'smallware'),
('bakeware', 'smallware'),
('bar supply', 'smallware'),
('bus box/rack', 'janitorial'),
('can liner', 'janitorial'),
('chafer', 'catering'),
('chair', 'furniture'),
('chinaware', 'tabletop'),
('cleaning apparel', 'janitorial'),
('cleaning supply', 'janitorial'),
('cooking', 'equipment'),
('countertop appliance', 'equipment'),
('cutlery', 'smallware'),
('d-bag', 'disposable'),
('d-bar supply', 'disposable'),
('d-chopstick', 'disposable'),
('d-container & tray', 'disposable'),
('d-cutlery & chopstick', 'disposable'),
('d-drink cup', 'disposable'),
('d-foodservice wrap & apparel', 'disposable'),
('d-napkin', 'disposable'),
('d-napkins/placement', 'disposable'),
('d-office supply', 'disposable'),
('d-portion cup', 'disposable'),
('d-soup cup', 'disposable'),
('d-sushi container', 'disposable'),
('detergent', 'janitorial'),
('electric appliance', 'equipment'),
('equipment parts', 'equipment'),
('flatware', 'tabletop'),
('floor mat', 'janitorial'),
('food', 'other'),
('food prep equipment', 'equipment'),
('food storage container', 'storage'),
('furniture parts', 'furniture'),
('gas & candle', 'catering'),
('glassware', 'tabletop'),
('holder & stand', 'tabletop'),
('ice machine', 'equipment'),
('internal use', 'other'),
('kitchenware', 'smallware'),
('melamine', 'tabletop'),
('misc', 'other'),
('rack & cart', 'equipment'),
('refrigeration', 'equipment'),
('screen', 'furniture'),
('serving tray', 'tabletop'),
('shelf', 'storage'),
('sign', 'other'),
('table', 'furniture'),
('towel/soap dispenser', 'janitorial'),
('trash container', 'janitorial'),
('warewashing', 'equipment'),
('warmer', 'catering'),
('worktable & stand', 'equipment'),
)

ITEM_D_DEPT = dict(ITEM_L_DEPT)


ITEM_D_CATE = {}
for k,v in ITEM_L_DEPT: ITEM_D_CATE.setdefault(v, []).append(k)
ITEM_L_CATE = ITEM_D_CATE.items()
ITEM_L_CATE.sort(key=lambda f_v: f_v[0])





