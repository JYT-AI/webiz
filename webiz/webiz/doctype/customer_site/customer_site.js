// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Site', {
	refresh(frm) {
		frm.trigger('setup_buttons');
		frm.trigger('set_customer_name');
	},

	setup_buttons(frm) {
		if (!frm.doc.__islocal) {
			// Add custom button to view site summary
			frm.add_custom_button(__('Site Summary'), function() {
				frm.call('get_site_summary').then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('Site Summary'),
							message: frm.trigger('format_site_summary', r.message),
							indicator: 'blue'
						});
					}
				});
			}, __('View'));

			// Add button to create related documents
			frm.add_custom_button(__('Create Task'), function() {
				frappe.new_doc('Task', {
					'subject': __('Task for {0}', [frm.doc.site_name]),
					'description': __('Task for site: {0}', [frm.doc.site_name])
				});
			}, __('Create'));

			frm.add_custom_button(__('Create Project'), function() {
				frappe.new_doc('Project', {
					'project_name': __('Project for {0}', [frm.doc.site_name]),
					'customer': frm.doc.customer
				});
			}, __('Create'));
		}
	},

	format_site_summary(frm, data) {
		let summary = `
			<div class="row">
				<div class="col-md-6">
					<p><strong>${__('Site Name')}:</strong> ${data.site_name || ''}</p>
					<p><strong>${__('Customer')}:</strong> ${data.customer || ''}</p>
					<p><strong>${__('Address')}:</strong> ${data.address || ''}</p>
					<p><strong>${__('Site Type')}:</strong> ${data.site_type || ''}</p>
				</div>
				<div class="col-md-6">
					<p><strong>${__('Status')}:</strong> ${data.status || ''}</p>
					<p><strong>${__('Priority')}:</strong> ${data.priority || ''}</p>
					<p><strong>${__('Total Area')}:</strong> ${data.total_area || ''} sq ft</p>
					<p><strong>${__('Contact')}:</strong> ${data.contact_person || ''} (${data.contact_phone || ''})</p>
				</div>
			</div>
		`;
		return summary;
	},

	customer(frm) {
		frm.trigger('set_customer_name');
	},

	set_customer_name(frm) {
		if (frm.doc.customer && !frm.doc.customer_name) {
			frappe.db.get_value('Customer', frm.doc.customer, 'customer_name')
				.then(r => {
					if (r.message && r.message.customer_name) {
						frm.set_value('customer_name', r.message.customer_name);
					}
				});
		}
	},

	validate(frm) {
		// Validate required fields
		if (!frm.doc.site_name) {
			frappe.msgprint(__('Site Name is required'));
			frappe.validated = false;
		}

		if (!frm.doc.customer) {
			frappe.msgprint(__('Customer is required'));
			frappe.validated = false;
		}

		// Validate email format
		if (frm.doc.email && !frappe.utils.validate_email_address(frm.doc.email)) {
			frappe.msgprint(__('Please enter a valid email address'));
			frappe.validated = false;
		}
	},

	site_type(frm) {
		// Set default values based on site type
		if (frm.doc.site_type) {
			let defaults = {
				'Office Building': {
					'facility_type': 'Indoor',
					'operating_hours': '9:00 AM - 6:00 PM'
				},
				'Factory': {
					'facility_type': 'Mixed',
					'operating_hours': '24/7'
				},
				'Warehouse': {
					'facility_type': 'Indoor',
					'operating_hours': '8:00 AM - 8:00 PM'
				},
				'Retail Store': {
					'facility_type': 'Indoor',
					'operating_hours': '10:00 AM - 10:00 PM'
				},
				'Hospital': {
					'facility_type': 'Indoor',
					'operating_hours': '24/7'
				},
				'School': {
					'facility_type': 'Mixed',
					'operating_hours': '7:00 AM - 6:00 PM'
				}
			};

			let site_defaults = defaults[frm.doc.site_type];
			if (site_defaults) {
				if (!frm.doc.facility_type) {
					frm.set_value('facility_type', site_defaults.facility_type);
				}
				if (!frm.doc.operating_hours) {
					frm.set_value('operating_hours', site_defaults.operating_hours);
				}
			}
		}
	}
});

// List view customization
frappe.listview_settings['Customer Site'] = {
	add_fields: ['customer_name', 'status', 'site_type', 'priority', 'city'],
	filters: [
		['status', '=', 'Active']
	],
	get_indicator: function(doc) {
		const status_colors = {
			'Active': 'green',
			'Inactive': 'red',
			'Under Maintenance': 'orange',
			'Closed': 'gray'
		};
		return [__(doc.status), status_colors[doc.status] || 'gray', 'status,=,' + doc.status];
	}
};
