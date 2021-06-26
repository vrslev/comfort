frappe.provide('comfort');

comfort.fetch_items = (item_codes, force_update=true, download_images=true) => {
	var promise = new Promise(resolve => {
		let isResolved = false;
		frappe.call({
			method: 'comfort.ikea.item.fetch_new_items',
			args: {
				item_codes: item_codes,
				force_update: force_update,
				download_images: download_images
			},
			callback: (r) => {
				if (r.message.unsuccessful.length > 0) {
					frappe.msgprint('Эти товары не удалось загрузить: ' + r.message.unsuccessful.join(', '));
				}
				frappe.dom.unfreeze();
				isResolved = true;
				resolve(r.message);
			}
		});
		setTimeout(() => {
			if (!isResolved) {
				frappe.dom.freeze();
			}
		}, 1000);
	});
	return promise;
};
