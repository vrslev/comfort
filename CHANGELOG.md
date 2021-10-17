<!-- prettier-ignore-start -->
# Changelog

<!--next-version-placeholder-->

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
