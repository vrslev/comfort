frappe.ready(function(){
	$('.add-to-cart').on('click', (e) => {
		$(e.currentTarget).prop('disabled', true);
		var item_name = $(e.currentTarget).data('item-name')
		if(frappe.session.user === 'Guest'){
			window.location.href = "/login"
		}
		else{
			frappe.call({
				method: 'accounting.accounting.doctype.sales_invoice.sales_invoice.add_to_cart',
				args: {
					item_name: item_name,
					qty: $('.qty').val(),
					user: frappe.session.user,
					save: true
				},
				callback: (r) => {
					$('.add-to-cart').prop('disabled', false)
					frappe.msgprint({
						title: 'Success',
						indicator: 'green',
						message: `<strong>${item_name}</strong> is successfully added to your <a href="/cart">Cart</a>`
					});
				}
			})
		}
	})
})