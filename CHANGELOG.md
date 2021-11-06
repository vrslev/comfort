<!-- prettier-ignore-start -->
# Changelog

<!--next-version-placeholder-->

## v0.26.2 (2021-11-06)
### Fix
* **Debtors report:** Show paid but not purchased orders amount; fix total amount color ([`6fd6b0d`](https://github.com/vrslev/comfort/commit/6fd6b0d8b357b4957b497fe2f3a4bcf4a770c524))

## v0.26.1 (2021-11-04)
### Fix
* **Delivery Trip:** Disable cache for driver mode ([`fcf4f78`](https://github.com/vrslev/comfort/commit/fcf4f78d74ae308aca78c1f80cccd7b5637af19c))

## v0.26.0 (2021-11-03)
### Feature
* **Sales Order:** Sort Purchase Order in listview filter by creation time ([`df99412`](https://github.com/vrslev/comfort/commit/df994125d57df300875f0b87d53a977ef6b0f6de))
* Add Debtors report ([`2d26c2e`](https://github.com/vrslev/comfort/commit/2d26c2ec3392b721ee8b800430bfe293eb9bf1fe))
* **Delivery Trip:** Use portal pages instead of Telegram for driver mode ([`255e56a`](https://github.com/vrslev/comfort/commit/255e56a33c477ddf3e7b31d31fd6ee473d7f93db))

### Fix
* **Sales Return:** Calculations in Purchase Order after all ([`1f440c7`](https://github.com/vrslev/comfort/commit/1f440c7f45e0e8adba1cc9a56f5d5f577aab6ad5))
* **Purchase Order:** Make customer field clickable ([`55dbe63`](https://github.com/vrslev/comfort/commit/55dbe63a49f29a60a862a1800539d84acb929a90))
* **Compensation:** Permissions to submit, cancel, amend ([`72bf19f`](https://github.com/vrslev/comfort/commit/72bf19faf37f2b925d2021fd42b6fb9366582388))
* **Compensation:** Translate "Received" button ([`f877cde`](https://github.com/vrslev/comfort/commit/f877cde54219264d503c6149a12957f409e611f2))
* **Sales Return:** Duplicate creation ([`e8adda5`](https://github.com/vrslev/comfort/commit/e8adda5d3c9d36ac0a1d98266c88a38c14fc2f07))
* Add Global Search translations ([`a56dd52`](https://github.com/vrslev/comfort/commit/a56dd5212a21ea5ed5d82f5310bfc291d5dcbdfe))
* **Customer:** Don't show undefined if no phone provided ([`b13f72c`](https://github.com/vrslev/comfort/commit/b13f72cce78dd5a85f2ec3d2a4e89d0eee62f182))
* Improve translations ([`60ad7ea`](https://github.com/vrslev/comfort/commit/60ad7ea59426fd80376a99bc3f40ca5bea44412e))
* Remove label on chart on Profit and Loss statement ([`54832d9`](https://github.com/vrslev/comfort/commit/54832d960ded2ecb6e0fbec2ad80f780cb3ac676))
* Stock Balance report item code align ([`2ce7a33`](https://github.com/vrslev/comfort/commit/2ce7a33848bf2eeb93bedd840b1166a81ea5c8e1))
* **Accounts:** Add missing translations ([`5f7d839`](https://github.com/vrslev/comfort/commit/5f7d83933f8986901400f4459ad38cb28fed099c))
* **Sales Order:** Status indicator appearance ([`cf6f85b`](https://github.com/vrslev/comfort/commit/cf6f85ba3c5f7b63e84e9f94ed31ccd90d9579c3))

## v0.25.0 (2021-11-02)
### Feature
* **Accounts:** Big fix for accounts ([`0b62aba`](https://github.com/vrslev/comfort/commit/0b62abaf73311c3db7bcb45e4afec545681714b9))

### Fix
* Migrate to new account system ([`4a67aaf`](https://github.com/vrslev/comfort/commit/4a67aaf6686dc0cb473b6c87c9d3740aa55dffac))
* **Receipt:** Don't create empty GL Entries ([`abda3c7`](https://github.com/vrslev/comfort/commit/abda3c710c61bf3ed14222ad9ed95fe56dc45eb8))

## v0.24.0 (2021-11-01)
### Feature
* **Sales Order:** Add Payment and Delivery indicators to form view ([`3a71a55`](https://github.com/vrslev/comfort/commit/3a71a5514472e382ce69b185f03f69dbcbc77aca))

### Fix
* **Translations:** Add missing translation ([`de3d5cd`](https://github.com/vrslev/comfort/commit/de3d5cd7320d5f36145820e2511fbb6965cbb461))
* Global Search availability ([`26907fa`](https://github.com/vrslev/comfort/commit/26907fac28f39465418032589cb71dde680b4d45))
* **Important:** Save document instead of db-updating on one-value changes (for example, status). ([`26ddc8c`](https://github.com/vrslev/comfort/commit/26ddc8c2f47f3d5cbf0137dc4f3de7701c8dce06))
* **Sales Order:** Incorrect item name in child items table ([`088d521`](https://github.com/vrslev/comfort/commit/088d5210a7adf9822c9fa41042d8f36f9ab7aa73))
* **queries:** Don't show None value ([`6912700`](https://github.com/vrslev/comfort/commit/6912700959a0109b5fa07e6d3741d99a2bb95f42))
* **Sales Order:** Payment and Delivery status appearance on old Windows notebook ([`7fb9903`](https://github.com/vrslev/comfort/commit/7fb990365c1e2315009deae03a8804ced10dc762))

## v0.23.0 (2021-11-01)
### Feature
* **Delivery Trip:** Format phone in telegram template ([`9c6dd6e`](https://github.com/vrslev/comfort/commit/9c6dd6eb41ded213e581dd6798453194fa801cbd))
* Format phone in frontend ([`d683b24`](https://github.com/vrslev/comfort/commit/d683b24a83512bafd13bd20f0ec5e395fdda3a7c))

### Fix
* **Sales Order:** Change pickup order message content if there's delivery ([`e6e2e51`](https://github.com/vrslev/comfort/commit/e6e2e515fd58127d5fa300e095c3cec7272bad23))
* **queries:** Return formatted phone or input value ([`a733af3`](https://github.com/vrslev/comfort/commit/a733af3fcdef04fb3f9d4378eaea623470c896e8))

## v0.22.4 (2021-11-01)
### Fix
* **Sales Order:** Change services on submit in some cases ([`070f21a`](https://github.com/vrslev/comfort/commit/070f21a5121c2b2cea17abdb81ae22778140c89c))
* **IKEA:** Retry to get authorized token ([`f16a4df`](https://github.com/vrslev/comfort/commit/f16a4df1c053ec5b4857f71dea9b65431b6a813a))
* **IKEA:** Another pretty error msg in order capture ([`e5beed7`](https://github.com/vrslev/comfort/commit/e5beed77613bf7501b0dcfd439f040f474224306))
* **Purchase Order:** Don't load Sales Order info if it does not exist ([`4fa4582`](https://github.com/vrslev/comfort/commit/4fa4582b7a5a73b3652a9d07102d6b968d697d10))

## v0.22.3 (2021-11-01)
### Fix
* Dump ikea-api-wrapped ([`b922e49`](https://github.com/vrslev/comfort/commit/b922e49b8ddfdd7b59b394b2fae59aae65f8f3dc))

## v0.22.2 (2021-10-31)
### Fix
* Translate values in queries, format phone number ([`058bdc1`](https://github.com/vrslev/comfort/commit/058bdc10314509593dd51cb9511f00cf058e0b00))
* **Translations:** Add missing translation ([`9ac32fb`](https://github.com/vrslev/comfort/commit/9ac32fb85d4727456fb57073a53e8d26ae668914))
* **Sales Order:** Format total amount in contract ([`9a22758`](https://github.com/vrslev/comfort/commit/9a227586b02dbe1cc18ca93e7e6edb3b81f15d65))
* **Item:** Remove duplicate item code filter ([`936dd9b`](https://github.com/vrslev/comfort/commit/936dd9b7b3464aa5432ba98e2aea5dcec859b1a4))
* **Delivery Trip:** "Add Multiple" button ([`6f4d5d4`](https://github.com/vrslev/comfort/commit/6f4d5d43af42ab95871836fd18406af5ac65fa3d))

## v0.22.1 (2021-10-30)
### Fix
* **Docker:** Fix build due to renaming branch of frappe/frappe_docker ([`356342b`](https://github.com/vrslev/comfort/commit/356342bbc008f51c092fd20f9221d7c9a1cfdfbd))

## v0.22.0 (2021-10-30)
### Feature
* Format money in templates ([`4d26bb5`](https://github.com/vrslev/comfort/commit/4d26bb57d80c41298c7a4fa9c559f2445a5cf618))
* **Purchase Order:** Show Sales Order name and Purchase Order name that has waiting for delivery orders in print format ([`24a62c4`](https://github.com/vrslev/comfort/commit/24a62c47eaff725480643cc900bbb449472552eb))
* Format item codes in print formats ([`53ed7ab`](https://github.com/vrslev/comfort/commit/53ed7ab807978a150eb90010cd2391c670c16f2b))
* Format item codes in frontend as IKEA does ([`40c2cc9`](https://github.com/vrslev/comfort/commit/40c2cc92562399c20d39429d5811dab1067748b5))
* **Purchase Order:** Add data about order in print format ([`2cc1725`](https://github.com/vrslev/comfort/commit/2cc1725e1f755e4811b12ee0692f703fcb64c16c))

### Fix
* **Purchase Order:** Don't allow to break page in middle of client ([`ce3cc31`](https://github.com/vrslev/comfort/commit/ce3cc317bef6e8959028d7d1194d3ea3cd496bf2))
* **Purchase Order:** Field order ([`37075ea`](https://github.com/vrslev/comfort/commit/37075ea82286238913f1b37dba07eccdddfd6e9a))

## v0.21.0 (2021-10-28)
### Feature
* **Waiting List:** Show message when Sales Order in Purchase Order ([`6b103b1`](https://github.com/vrslev/comfort/commit/6b103b13586a9a8e37a846e72ba0673424c4f012))

### Fix
* Add Waiting List to global search ([`c6425d1`](https://github.com/vrslev/comfort/commit/c6425d1281a2790c61179062baa2d5d29d202ffa))
* **Sales Order:** Don't show cancelled orders in Not In PO filter ([`e0b7f24`](https://github.com/vrslev/comfort/commit/e0b7f24571c1185581a55166cc831f1fff680feb))

## v0.20.0 (2021-10-28)
### Feature
* **Purchase Order:** Add `total_margin` field ([`6888eb2`](https://github.com/vrslev/comfort/commit/6888eb275ee01fef84446d2c1069ca14f9eaa4d3))

## v0.19.1 (2021-10-28)
### Fix
* **Sales Order:** Delivery status for order from available actual stock ([`86f5694`](https://github.com/vrslev/comfort/commit/86f569424b4be4e4f3b93a8265cc5d8ffacb2eaf))
* **Sales Order:** Notice about delivery and installation in contracts ([`a882710`](https://github.com/vrslev/comfort/commit/a882710221b3c8d776da60250db31cfe1135a93d))

## v0.19.0 (2021-10-26)
### Feature
* Add Waiting List ([`e24b965`](https://github.com/vrslev/comfort/commit/e24b9654227c2a45d3dff72bc53ffbf787c9575f))

## v0.18.3 (2021-10-25)
### Fix
* **UI:** Translations for upcoming changes (https://github.com/frappe/frappe/pull/14573) ([`d21dd58`](https://github.com/vrslev/comfort/commit/d21dd581cd8fe2cb57111f5f2ff2477882ecd056))
* **IKEA:** Add missing translation ([`9b8bfcb`](https://github.com/vrslev/comfort/commit/9b8bfcb3dfed3011ff13f364f50dd568e401dc38))

## v0.18.2 (2021-10-25)
### Fix
* Frappe version ([`7b2d9c7`](https://github.com/vrslev/comfort/commit/7b2d9c7b9f784cff8e03ee4d2fe9564b5166a7b6))

## v0.18.1 (2021-10-25)
### Fix
* Revert frappe update ([`1017186`](https://github.com/vrslev/comfort/commit/1017186b02fe64e2707ef14b30631f7d8b204a49))

## v0.18.0 (2021-10-25)
### Feature
* **Purchase Order:** Improve print format ([`33e1206`](https://github.com/vrslev/comfort/commit/33e12067e1a97c7471b4b8f1a8d7728a514a2017))

### Fix
* **IKEA:** Handle internal Order Capture error (closes #62) ([`b11b81f`](https://github.com/vrslev/comfort/commit/b11b81f44d338bd70f97bc725b50a392209e8531))
* **Sentry:** Don't capture connection reset in rq and auth fail ([`bc47e7a`](https://github.com/vrslev/comfort/commit/bc47e7a6bbd0f923bbff52dfb83da51be7a29e1f))
* **Purchase Order:** Clear no-copy fields on amend ([`ff83c73`](https://github.com/vrslev/comfort/commit/ff83c73ef4328d6f85477edf88c768b169f06fb8))
* **Sales Return:** Save Sales Order with validations ([`62146dc`](https://github.com/vrslev/comfort/commit/62146dc76b4be9948781a753dd8bb32697a8e73d))

## v0.17.0 (2021-10-23)
### Feature
* **Delivery Trip:** Calculate total weight ([`835e037`](https://github.com/vrslev/comfort/commit/835e037e91c0e8235c303f384962247bc072d673))

### Fix
* **Sales Order:** Allow to check availability if delivery status is "To  Purchase" and docstatus is 1; fix "Open In VK" btn appearance ([`f500565`](https://github.com/vrslev/comfort/commit/f500565ad5a34924bba81b83aeb312693e1ee741))
* **Sentry:** Remove performance monitoring ([`ea0beff`](https://github.com/vrslev/comfort/commit/ea0beffa9a463a0db9cd04c4cdd4103e962a80df))

## v0.16.1 (2021-10-20)
### Fix
* **Translations:** Don't load translations in other languages ([`f2c95c8`](https://github.com/vrslev/comfort/commit/f2c95c81878118fce9c76a2d4d28d3971363553d))

## v0.16.0 (2021-10-20)
### Feature
* **Sales Order:** Add pending amount to pickup order msg ([`3b17b50`](https://github.com/vrslev/comfort/commit/3b17b50811d750caf0bdf1900798dac8dfbdb856))

### Fix
* Some translations appearance ([`108306a`](https://github.com/vrslev/comfort/commit/108306a1a791c3007c86c03277df422d3c30b9a3))

## v0.15.3 (2021-10-20)
### Fix
* **Purchase Order:** Fetch items for submitted Sales Orders before submit ([`ed27e96`](https://github.com/vrslev/comfort/commit/ed27e96a6a737016e35bd7665b5ca0454112de0a))
* **Purchase Order:** Freeze when fetching items on submit ([`1a84cbf`](https://github.com/vrslev/comfort/commit/1a84cbff2c3bc92920e667878859446a7d523905))
* **Sales Order:** Don't try to cancel cancelled Payments or Receipts ([`13161a1`](https://github.com/vrslev/comfort/commit/13161a15945e3f679389eedba559742375a7561d))

## v0.15.2 (2021-10-20)
### Fix
* **Sales Order:** Cancel orders linked to cancelled PO ([`9093458`](https://github.com/vrslev/comfort/commit/909345855ab0ad1a0fe671919d9df5f60e549c5b))
* **Purchase Order:** Include Sales Orders linked to cancelled Purchase Orders in query ([`ed1b58a`](https://github.com/vrslev/comfort/commit/ed1b58a030d6facd9fe4e14957fe5eb0c0fa706f))
* **Sales Order:** Not In PO filter was showing orders in cancelled PO ([`b9506af`](https://github.com/vrslev/comfort/commit/b9506afa340d56ae6b3b4de81b205c3567a3bd31))

## v0.15.1 (2021-10-20)
### Fix
* **Sales Order:** Cancel after cancelling Purchase Order ([`523e890`](https://github.com/vrslev/comfort/commit/523e89087715ba25643db3d9a78f77a201cf4949))
* **Sales Order:** Diff commission when splitting order ([`4074a2c`](https://github.com/vrslev/comfort/commit/4074a2cc95d747c20f085f54aa9d524578b9d7d7))
* Hide unused modules ([`9dd80f5`](https://github.com/vrslev/comfort/commit/9dd80f521e8fc73ec94d0c478d389b200abe1a39))

## v0.15.0 (2021-10-19)
### Feature
* **Sales Order:** Add contract print template (closes #34) ([`ea1ea77`](https://github.com/vrslev/comfort/commit/ea1ea777c5fc92ba62fa8aaf3a70aa7a351a29d9))

### Fix
* Hide unused modules ([`1333a37`](https://github.com/vrslev/comfort/commit/1333a3703d5ee52f465a34928b3a0c80689f0274))

## v0.14.0 (2021-10-18)
### Feature
* **Item:** Add item dashboard ([`35190c6`](https://github.com/vrslev/comfort/commit/35190c6ab220b94d305491ed349ec146f623d122))

### Fix
* **Purchase Order:** Make reference fields no-copy ([`f7e5a0e`](https://github.com/vrslev/comfort/commit/f7e5a0ee5155d575d9a1df88444891699102173b))
* **Purchase Order:** Cancellation ([`d9be160`](https://github.com/vrslev/comfort/commit/d9be160c9eda47c315a3ce63194b7e0442133656))
* **Purchase Order:** Cancel when there's Sales Orders from available stock ([`fe33b49`](https://github.com/vrslev/comfort/commit/fe33b49e3253fe8dda7aa6d45023f8e09ae86e0b))
* **Sentry:** Don't send mysql conn errors ([`b26c9f3`](https://github.com/vrslev/comfort/commit/b26c9f3789a3863547f5bd51671ae976040d54eb))

## v0.13.0 (2021-10-17)
### Feature
* **Compensation:** Add `notes` field ([`09af98d`](https://github.com/vrslev/comfort/commit/09af98dcb1a4c19b3fdc6f97bc41d1fed13581f7))

### Fix
* **Browser Ext:** Accept json as response for better error reports ([`1367ecf`](https://github.com/vrslev/comfort/commit/1367ecf16dc10a3919a818421fa49d32062670c5))
* **Translations:** Translate some stuff ([`1dec93f`](https://github.com/vrslev/comfort/commit/1dec93ff05b7a556199c756381c73c245feb1336))
* **Purchase Order:** Don't set mock schedule date ([`78a62f0`](https://github.com/vrslev/comfort/commit/78a62f09aa887cb67a87c19df2df9b7d17fdf71b))

## v0.12.1 (2021-10-17)
### Fix
* **Customer:** VK URL parsing ([`711410e`](https://github.com/vrslev/comfort/commit/711410e7edbb878c2e60075af760974643341c30))

## v0.12.0 (2021-10-16)
### Feature
* **Compensation:** Add status ([`6443739`](https://github.com/vrslev/comfort/commit/6443739a81377a0fa69fb69e9900125b5e74fa02))
* Redirect from root to /app ([`dcb99db`](https://github.com/vrslev/comfort/commit/dcb99dbe13165e2b0514e9702d43f3f2b4142941))

### Fix
* Hide unused workspaces ([`2d399c5`](https://github.com/vrslev/comfort/commit/2d399c57d1b015bd5d6a300143335a289a951f53))
* **IKEA:** Don't use auth server in dev mode ([`ea4cdcf`](https://github.com/vrslev/comfort/commit/ea4cdcf748898d971a6c332c883985a749b9ba41))

## v0.11.0 (2021-10-16)
### Feature
* **Sales Order:** Add Purchase Order filter ([`54f0748`](https://github.com/vrslev/comfort/commit/54f07484983069411da7ee6c99452fd7d7d82c39))

### Fix
* Add after_migrate hook ([`83f2b8b`](https://github.com/vrslev/comfort/commit/83f2b8bbde5a6a51aa651708463b4413d24d7349))
* **Item Category:** URL Validation ([`8bebb4e`](https://github.com/vrslev/comfort/commit/8bebb4e87b57653577d020812b01906b7f032919))

## v0.10.1 (2021-10-16)
### Fix
* **Profit and Loss report:** Intermediate calculations ([`9b7cc71`](https://github.com/vrslev/comfort/commit/9b7cc71b7ce6801de20970a7ca053d50649c9172))

## v0.10.0 (2021-10-15)
### Feature
* Extend session expiry to 30 days; use better number format ([`265d9d9`](https://github.com/vrslev/comfort/commit/265d9d92ac7abe9d9b84a95f3ee28342c0a15bca))

### Fix
* **Queries:** Full text search on all search fields ([`0b33788`](https://github.com/vrslev/comfort/commit/0b337887ec8f5b5fb7a10760b4364a17cad2eac6))
* **Translations:** Now — сейчас ([`6dfbb46`](https://github.com/vrslev/comfort/commit/6dfbb46bacedbf4bda4f170a1d6814ef41c5f313))
* **Deployment:** Prune old images and remove orphans ([`ff48c68`](https://github.com/vrslev/comfort/commit/ff48c6863647da9e72e69d0080016c357ce041a9))
* **Sales Order:** Don't show orders from available stock in Not in PO filter ([`255932a`](https://github.com/vrslev/comfort/commit/255932a1e86e9b28529e5eb4af91ee7b08f45180))
* **Customer:** Clean VK URL on save ([`d4180a7`](https://github.com/vrslev/comfort/commit/d4180a7ac479535bbb86f4dba5b3fb6b18d3776b))
* **Customer:** Don't require vk integration ([`6daab7b`](https://github.com/vrslev/comfort/commit/6daab7b8518028ccbb6b6a0c92760b577cc05c60))
* **Customer:** Deal with naming in object ([`6546a9b`](https://github.com/vrslev/comfort/commit/6546a9bac9e69a1b911f753449353c2f828654b0))
* **IKEA:** Throw on no items ([`817210b`](https://github.com/vrslev/comfort/commit/817210bdba37f5b3a0e3386851557d8db84bfb2c))
* **Commission Settings:** Error on fresh doc ([`10565c9`](https://github.com/vrslev/comfort/commit/10565c9ea8eec77948dd1cbb04d40a18fcf041b0))
* **Sales Order:** `NaN` amounts on new doc ([`bfaf832`](https://github.com/vrslev/comfort/commit/bfaf8324f8039383ce8e9fb8b7ade38476674271))
* **Sales Order:** More meaningful err msg on insufficient stock ([`8431abb`](https://github.com/vrslev/comfort/commit/8431abb68e5f8daf5bf8ff1abcd386afeeef1133))
* **Translations:** Vk Api Settings and Ikea Authorization Server Settings ([`37f3c6e`](https://github.com/vrslev/comfort/commit/37f3c6e95b3b8447a310882f1af1a7aa04e05cd1))
* **Purchase Order:** Force `only_select` in Sales Order ([`3dbbf65`](https://github.com/vrslev/comfort/commit/3dbbf658caa384c7cc768db4fdc79142c2ecb9cb))
* **Delivery Trip:** KeyError on submit no services ([`cfb5435`](https://github.com/vrslev/comfort/commit/cfb54350ae0f3fa8fb4ae176a6d3c55850030b02))
* **IKEA:** Fix freeze and handle errors in frontend's `get_items` ([`717a767`](https://github.com/vrslev/comfort/commit/717a76769c21e8587720751cb38bdc81287f9477))
* **IKEA:** Pretty msg on `ItemFetchError` if can ([`709e0a9`](https://github.com/vrslev/comfort/commit/709e0a9836cc293f6e30207fc492310c368a707e))
* **Purchase Order:** `NaN` value on table fields change ([`1d93396`](https://github.com/vrslev/comfort/commit/1d93396b6691563b8da6cf4c143e7d4e514d062f))
* **Purchase Order:** Has-no-attr errors ([`d12a403`](https://github.com/vrslev/comfort/commit/d12a40354a8a7aa729003e16b2736191a7cf8bde))
* **Purchase Order:** Set default values for Delivery and Sales Order costs ([`a8438e6`](https://github.com/vrslev/comfort/commit/a8438e6a1afdf065bf43914e36b7319627674e11))

## v0.9.0 (2021-10-15)
### Feature
* **IKEA:** Add authorization server and client ([`536b7b1`](https://github.com/vrslev/comfort/commit/536b7b1c85983860648db06bd207ed4780c8b74c))

## v0.8.1 (2021-10-14)
### Fix
* **Quick Add Items:** Show added row in PO, don't add empty rows in SO ([`34dbde6`](https://github.com/vrslev/comfort/commit/34dbde6fb249357782df483a381af7b8bccc0887))
* **Purchase Order and Sales Order:** Allow to remove multiple items/orders in grids ([`18f236f`](https://github.com/vrslev/comfort/commit/18f236f3e6a72f7a414318c445e3bd7cbdd674d5))

## v0.8.0 (2021-10-14)
### Feature
* Merge pull request #47 from vrslev/tests ([`242af32`](https://github.com/vrslev/comfort/commit/242af3218abaa3ea2fb0f395bf78a1545437fb4b))

## v0.7.2 (2021-10-14)
### Fix
* **IKEA:** Circular import ([`45a0f9d`](https://github.com/vrslev/comfort/commit/45a0f9d4276e63f1c2d5212391f57713027f9fa6))

## v0.7.1 (2021-10-13)
### Fix
* **IKEA:** Add translation in `get_delivery_services` ([`755cae7`](https://github.com/vrslev/comfort/commit/755cae7948514c4e00bdabe55e2591092de52518))
* **Customer:** Simplify vk id parsing ([`e59acaa`](https://github.com/vrslev/comfort/commit/e59acaa9b5fc9f9ef208533f9a51c32f7edc4d72))
* **Commission Settings:** Don't allow same `to_amount` ([`bd1be6a`](https://github.com/vrslev/comfort/commit/bd1be6a49258dce36a226b014553dd3f0bf29e4f))
* **Commands:** Don't delete settings on cleanup and use `frappe.db.delete` ([`ef9288f`](https://github.com/vrslev/comfort/commit/ef9288f29487f83b0d35cdf4bafc9b98b873d22c))
* **Sentry:** Ignore `ValidationError` ([`6be49a2`](https://github.com/vrslev/comfort/commit/6be49a2f9544171046e4ce8ae90538897bd6c70f))
* **IKEA:** Don't store item images ([`e13c74c`](https://github.com/vrslev/comfort/commit/e13c74c8c4b94b381a04dd53a02119da6abfea2c))

## v0.7.0 (2021-10-13)
### Feature
* **VK:** Update info weekly and on customer save ([`ef2d0f4`](https://github.com/vrslev/comfort/commit/ef2d0f491baf622e63edf78cc145cc236a32225a))
* **VK:** Add VK API client ([`c26a022`](https://github.com/vrslev/comfort/commit/c26a022ebaedcb90c3bdc3a73a5018aa1c0dbd74))

### Fix
* **VK:** Show customer image ([`21cc894`](https://github.com/vrslev/comfort/commit/21cc89417f0d69776907914e000ddec0288e1eba))

## v0.6.1 (2021-10-13)
### Fix
* **Settings:** Clear cache on change ([`55a3269`](https://github.com/vrslev/comfort/commit/55a326994f12fdf364bfaad4534bd2ad44856284))

## v0.6.0 (2021-10-12)
### Feature
* Empty commit ([`f9fd7dd`](https://github.com/vrslev/comfort/commit/f9fd7dd492e787672dd870370372def805dae9db))

## v0.5.3 (2021-10-11)
### Fix
* **Sales Order:** Copying messages ([`d1f8e10`](https://github.com/vrslev/comfort/commit/d1f8e10dbaa0cc76e05b9b57a28a3235513293a2))

## v0.5.2 (2021-10-11)
### Fix
* Permissions ([`3e31e9d`](https://github.com/vrslev/comfort/commit/3e31e9d416ab0d5b208a36a42db387d0ff1d3b48))

## v0.5.1 (2021-10-11)
### Fix
* **Sentry:** Did not initialize ([`279b197`](https://github.com/vrslev/comfort/commit/279b197fa30455e7ec790cc823717007e47f83ee))

## v0.5.0 (2021-10-10)
### Feature
* **Purchase Order:** Fetch items specs before submit ([`9ae1940`](https://github.com/vrslev/comfort/commit/9ae19401a825dba90d9a47e47606f82b355a6bfb))
* Add Compensation doctype ([`9e4b811`](https://github.com/vrslev/comfort/commit/9e4b811719804c7657b52926129127db4dd322e6))
* **Purchase Order:** Add print format ([`4c0539f`](https://github.com/vrslev/comfort/commit/4c0539feb05e30f3b1a83cb1b2412493ceb5dde9))
* **Customer and Sales Order:** Add "Open in VK" button ([`4b1d52d`](https://github.com/vrslev/comfort/commit/4b1d52de15783f6941e0af5d87aa0ec090cc3159))

### Fix
* **Purchase Order:** Translation ([`2df2fd9`](https://github.com/vrslev/comfort/commit/2df2fd93680884593f124d429b3c0d53c7ec24c3))
* **Profit and Loss:** Add translations ([`1fe0897`](https://github.com/vrslev/comfort/commit/1fe0897a3e3ce3e7b9186b65fe0e7c1315cad95c))
* **General Ledger:** Translate doctypes ([`c5df739`](https://github.com/vrslev/comfort/commit/c5df739dd6910491d986f1a86c5329f2746c0dd2))
* **IKEA:** Handle no zip_code exception ([`dd4fb4c`](https://github.com/vrslev/comfort/commit/dd4fb4c58b861ae63579be292c433f2a377b891f))
* **Translations:** Improve translations ([`353ea74`](https://github.com/vrslev/comfort/commit/353ea7448006c2700c40e667a880d7bf29a8379b))
* **Browser Ext:** Python script path ([`337857f`](https://github.com/vrslev/comfort/commit/337857fc0ad8dc6db78be46e00aa8c47567821cf))

## v0.4.0 (2021-10-10)
### Feature
* **Purchase Order:** Fetch items specs before submit ([`1724342`](https://github.com/vrslev/comfort/commit/17243426ca62796eb6742a96541318aceced8024))
* Add Compensation doctype ([`ae4f20f`](https://github.com/vrslev/comfort/commit/ae4f20fcf33cec4d68b92e112d7563e5124ca94e))
* **Purchase Order:** Add print format ([`85b851c`](https://github.com/vrslev/comfort/commit/85b851c55bc88643b634b02e7bfe97098724213e))
* **Customer and Sales Order:** Add "Open in VK" button ([`3a5b01a`](https://github.com/vrslev/comfort/commit/3a5b01a01b86545c53cb65b044f08b5aa2a2b012))

### Fix
* **Browser Ext:** Request to server ([`41ac532`](https://github.com/vrslev/comfort/commit/41ac5328775d9b4597126133e83c24734eb8de29))
* **Browser Ext:** Python script path ([`e49a7e2`](https://github.com/vrslev/comfort/commit/e49a7e272335fa29e04e019519454a981115fdb1))

## v0.3.4 (2021-10-09)
### Fix
* **VK Form:** VK URL building ([`c54b4c5`](https://github.com/vrslev/comfort/commit/c54b4c56d888918c15f06d5c4c4879b7ad64c5f4))

## v0.3.3 (2021-10-09)
### Fix
* **VK Form:** Commit ([`86cb43a`](https://github.com/vrslev/comfort/commit/86cb43a9e5ddfb498f2b7ac3c53ad33560c7b052))
* **VK Form:** Add translations ([`da0ed62`](https://github.com/vrslev/comfort/commit/da0ed62663ca57b88794a4c9efeb2e5857de8dd1))

## v0.3.2 (2021-10-09)
### Fix
* **VK Form:** Remove confirmation thing ([`b213b7f`](https://github.com/vrslev/comfort/commit/b213b7f9f6bf291bbf0983ae630a8a90c404eddd))

## v0.3.1 (2021-10-09)
### Fix
* Add vk form settings to search ([`5381f07`](https://github.com/vrslev/comfort/commit/5381f073d499dc9a93b8f70ab8406a79dd4f16b3))
* Add pydantic dependency ([`b4049f8`](https://github.com/vrslev/comfort/commit/b4049f815b67541785b9e7af6980f182ef774dc0))

## v0.3.0 (2021-10-09)
### Feature
* Add VK Form integration ([`8d047b9`](https://github.com/vrslev/comfort/commit/8d047b9908fc195e7b8cf278e07fb91f2cba4b64))

## v0.2.1 (2021-10-08)
### Fix
* Disable Signup ([`02b58cd`](https://github.com/vrslev/comfort/commit/02b58cd188e5f49d004e1531cffb59a69dd92871))
* Add Module Profile for restriction ([`77fabf7`](https://github.com/vrslev/comfort/commit/77fabf788d46268b4867ee1aca9bc6c5a9cfdaca))
* Hide unused modules on homepage in production ([`adcbcef`](https://github.com/vrslev/comfort/commit/adcbcef48d2c417feaeb851276fad5b7c4953e7b))

## v0.2.0 (2021-10-08)
### Feature
* **Delivery Trip:** Installation note to template ([`3e38805`](https://github.com/vrslev/comfort/commit/3e38805d33d6a4ea5e946c8040819edae946e727))
* **Docker:** Enable Sentry ([`9ad0193`](https://github.com/vrslev/comfort/commit/9ad01934a44c0cc93ef19bbe394ac46a1ca08dcd))
* **Delivery Trip:** Validations, updating info ([`2893b6c`](https://github.com/vrslev/comfort/commit/2893b6cd4e6ebda9a4340d46dea52a54d0ed1d82))

### Fix
* **Delivery Trip:** Force `only_select` ([`e24ea08`](https://github.com/vrslev/comfort/commit/e24ea087213f51b00e9c7da807da2520ba0790db))
* **Sales Order:** Services on submit ([`9015f3b`](https://github.com/vrslev/comfort/commit/9015f3bbb6a190a3efead3b5b103e1b5053a485d))
* **Sales Order:** Don't allow to fetch items if from Available Stock ([`ed23ec4`](https://github.com/vrslev/comfort/commit/ed23ec480e10ceb63d283802f385e9cc35134212))
* **Browser Ext:** Allow not to select any text ([`9beb533`](https://github.com/vrslev/comfort/commit/9beb533a3b8ec50594cd7377daed20ae7e92506f))
* **Sales Order:** From Available Stock didn't have impact ([`923eaa1`](https://github.com/vrslev/comfort/commit/923eaa12e04e426be42aa63a64a50a9329bbdc21))
* **Translations:** Add for Purchase Order ([`0102d27`](https://github.com/vrslev/comfort/commit/0102d27072277b2dd39c8b2b10331bb47241c5e3))
* **Sales Order:** Add filter to From Available Stock prompt ([`f2a89e9`](https://github.com/vrslev/comfort/commit/f2a89e93b196e4f4734fb7c63a792f8fb7a6c8a0))
* **Sales Order:** Delivery service rates ([`a463a0d`](https://github.com/vrslev/comfort/commit/a463a0d24f8a60c4b181b4f7cbb83abcf0eb1ed7))
* **Purchase Order:** Submit event crashes ([`7554857`](https://github.com/vrslev/comfort/commit/7554857e283e439e61a459d3b825c9fe87729908))

## v0.1.1 (2021-10-08)
### Fix
* **Translations:** Translations in Purchase Order ([`e9a249a`](https://github.com/vrslev/comfort/commit/e9a249a4eb81fcae53b25f3fafe46dba122fe0ea))
* **Translations:** Cash or Bank in Sales Order ([`5534da4`](https://github.com/vrslev/comfort/commit/5534da403c8b6f68f7f1767f532a12bcffcec9ac))

## v0.1.0 (2021-10-07)
Initial release!
<!-- prettier-ignore-end -->
