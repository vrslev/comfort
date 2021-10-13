<!-- prettier-ignore-start -->
# Changelog

<!--next-version-placeholder-->

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
