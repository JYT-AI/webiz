// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facility Checklist Template', {
	refresh(frm) {
		frm.trigger('setup_buttons');
		frm.trigger('set_created_by');
		frm.trigger('setup_checklist_grid');
	},

	setup_buttons(frm) {
		if (!frm.doc.__islocal) {
			// Add custom buttons
			frm.add_custom_button(__('Preview Checklist'), function() {
				frm.call('get_checklist_config').then(r => {
					if (r.message) {
						frm.trigger('show_checklist_preview', r.message);
					}
				});
			}, __('View'));

			frm.add_custom_button(__('Duplicate Template'), function() {
				frappe.prompt({
					label: __('New Template Name'),
					fieldname: 'new_name',
					fieldtype: 'Data',
					reqd: 1
				}, function(values) {
					frm.call('duplicate_template', {
						new_name: values.new_name
					}).then(r => {
						if (r.message) {
							frappe.msgprint(__('Template duplicated successfully'));
							frappe.set_route('Form', 'Facility Checklist Template', r.message.name);
						}
					});
				}, __('Duplicate Template'));
			}, __('Actions'));

			frm.add_custom_button(__('Usage Statistics'), function() {
				frm.trigger('show_usage_stats');
			}, __('View'));
		}
	},

	show_checklist_preview(frm, config) {
		let preview_html = `
			<div class="checklist-preview">
				<h4>${config.template_name}</h4>
				<p><strong>${__('Description')}:</strong> ${config.description || ''}</p>
				<p><strong>${__('Estimated Time')}:</strong> ${config.estimated_time || 0} hours</p>
				<p><strong>${__('Facility Type')}:</strong> ${config.facility_type}</p>
				<p><strong>${__('Site Type')}:</strong> ${config.site_type || 'All'}</p>
				
				<h5>${__('Checklist Items')}:</h5>
				<ol>
		`;

		config.items.forEach(item => {
			preview_html += `
				<li>
					<strong>${item.title}</strong> (${item.type})
					${item.mandatory ? '<span class="text-danger">*</span>' : ''}
					${item.description ? `<br><small>${item.description}</small>` : ''}
					${item.estimated_time ? `<br><small>Est. Time: ${item.estimated_time} min</small>` : ''}
				</li>
			`;
		});

		preview_html += `
				</ol>
			</div>
		`;

		frappe.msgprint({
			title: __('Checklist Preview'),
			message: preview_html,
			wide: true
		});
	},

	show_usage_stats(frm) {
		let stats_html = `
			<div class="usage-stats">
				<h4>${__('Usage Statistics')}</h4>
				<p><strong>${__('Usage Count')}:</strong> ${frm.doc.usage_count || 0}</p>
				<p><strong>${__('Last Used')}:</strong> ${frm.doc.last_used ? frappe.datetime.str_to_user(frm.doc.last_used) : 'Never'}</p>
				<p><strong>${__('Created By')}:</strong> ${frm.doc.created_by || ''}</p>
				<p><strong>${__('Approved By')}:</strong> ${frm.doc.approved_by || 'Not Approved'}</p>
			</div>
		`;

		frappe.msgprint({
			title: __('Usage Statistics'),
			message: stats_html
		});
	},

	set_created_by(frm) {
		if (frm.doc.__islocal && !frm.doc.created_by && frappe.session.user) {
			frm.set_value('created_by', frappe.session.user);
		}
	},

	setup_checklist_grid(frm) {
		// Customize checklist items grid
		frm.fields_dict.checklist_items.grid.get_field('item_sequence').df.columns = 1;
		frm.fields_dict.checklist_items.grid.get_field('item_title').df.columns = 3;
		frm.fields_dict.checklist_items.grid.get_field('item_type').df.columns = 2;
		frm.fields_dict.checklist_items.grid.get_field('is_mandatory').df.columns = 1;
	},

	facility_type(frm) {
		frm.trigger('update_estimated_time');
	},

	site_type(frm) {
		frm.trigger('check_default_template');
	},

	is_default(frm) {
		frm.trigger('check_default_template');
	},

	check_default_template(frm) {
		if (frm.doc.is_default && frm.doc.facility_type) {
			// Check if another default template exists
			frappe.call({
				method: 'webiz.webiz.doctype.facility_checklist_template.facility_checklist_template.get_default_template',
				args: {
					facility_type: frm.doc.facility_type,
					site_type: frm.doc.site_type
				},
				callback: function(r) {
					if (r.message && r.message.name !== frm.doc.name) {
						frappe.msgprint({
							title: __('Warning'),
							message: __('Another default template exists: {0}. Setting this as default will override the existing one.', [r.message.template_name]),
							indicator: 'orange'
						});
					}
				}
			});
		}
	},

	update_estimated_time(frm) {
		// Calculate total estimated time from checklist items
		let total_time = 0;
		if (frm.doc.checklist_items) {
			frm.doc.checklist_items.forEach(item => {
				if (item.estimated_time) {
					total_time += item.estimated_time;
				}
			});
		}
		
		// Convert minutes to hours
		frm.set_value('estimated_time', total_time / 60);
	},

	validate(frm) {
		// Validate template name
		if (!frm.doc.template_name) {
			frappe.msgprint(__('Template Name is required'));
			frappe.validated = false;
		}

		// Validate checklist items
		if (!frm.doc.checklist_items || frm.doc.checklist_items.length === 0) {
			frappe.msgprint(__('At least one checklist item is required'));
			frappe.validated = false;
		}

		// Check for duplicate sequences
		if (frm.doc.checklist_items) {
			let sequences = [];
			let has_duplicate = false;
			
			frm.doc.checklist_items.forEach(item => {
				if (sequences.includes(item.item_sequence)) {
					has_duplicate = true;
				}
				sequences.push(item.item_sequence);
			});

			if (has_duplicate) {
				frappe.msgprint(__('Duplicate sequence numbers found in checklist items'));
				frappe.validated = false;
			}
		}
	}
});

// Child table events for Facility Checklist Item
frappe.ui.form.on('Facility Checklist Item', {
	checklist_items_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		// Set default sequence number
		let max_sequence = 0;
		if (frm.doc.checklist_items) {
			frm.doc.checklist_items.forEach(item => {
				if (item.item_sequence > max_sequence) {
					max_sequence = item.item_sequence;
				}
			});
		}
		frappe.model.set_value(cdt, cdn, 'item_sequence', max_sequence + 1);
	},

	estimated_time(frm, cdt, cdn) {
		frm.trigger('update_estimated_time');
	},

	item_type(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_type === 'Multiple Choice' && !row.check_options) {
			frappe.model.set_value(cdt, cdn, 'check_options', 'Option 1\nOption 2\nOption 3');
		}
	}
});

// List view customization
frappe.listview_settings['Facility Checklist Template'] = {
	add_fields: ['facility_type', 'site_type', 'status', 'is_default', 'usage_count'],
	filters: [
		['status', '=', 'Active']
	],
	get_indicator: function(doc) {
		const status_colors = {
			'Active': 'green',
			'Inactive': 'red',
			'Draft': 'orange',
			'Archived': 'gray'
		};
		
		let indicator = [__(doc.status), status_colors[doc.status] || 'gray', 'status,=,' + doc.status];
		
		if (doc.is_default) {
			indicator[0] += ' (Default)';
			indicator[1] = 'blue';
		}
		
		return indicator;
	}
};
