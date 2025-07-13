// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Task', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.is_template && frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Create Work Session'), function() {
				create_work_session(frm);
			});
			
			frm.add_custom_button(__('View Sessions'), function() {
				frappe.set_route('List', 'Work Session', {
					work_task: frm.doc.name
				});
			});
			
			if (frm.doc.auto_repeat_enabled) {
				frm.add_custom_button(__('Preview Schedule'), function() {
					preview_schedule(frm);
				});
			}
		}
		
		// Set filters
		set_filters(frm);
		
		// Show template indicator
		if (frm.doc.is_template) {
			frm.dashboard.add_indicator(__('Template'), 'blue');
		}
	},
	
	work_project: function(frm) {
		// Filter customer sites based on work project
		if (frm.doc.work_project) {
			frappe.db.get_value('Work Project', frm.doc.work_project, 'customer')
				.then(r => {
					if (r.message && r.message.customer) {
						frm.set_query('customer_site', function() {
							return {
								filters: {
									customer: r.message.customer
								}
							};
						});
					}
				});
		}
	},
	
	is_template: function(frm) {
		// Toggle template-specific fields
		if (frm.doc.is_template) {
			frm.set_value('status', 'Template');
		} else {
			frm.set_value('status', 'Open');
			frm.set_value('auto_repeat_enabled', 0);
		}
	},
	
	auto_repeat_enabled: function(frm) {
		// Set default values when auto repeat is enabled
		if (frm.doc.auto_repeat_enabled && !frm.doc.repeat_start_date) {
			frm.set_value('repeat_start_date', frappe.datetime.get_today());
		}
	},
	
	repeat_start_date: function(frm) {
		validate_repeat_dates(frm);
	},
	
	repeat_end_date: function(frm) {
		validate_repeat_dates(frm);
	},
	
	customer_site: function(frm) {
		// Auto-set checklist template based on customer site
		if (frm.doc.customer_site) {
			frappe.db.get_value('Customer Site', frm.doc.customer_site, 'default_checklist_template')
				.then(r => {
					if (r.message && r.message.default_checklist_template) {
						frm.set_value('checklist_template', r.message.default_checklist_template);
					}
				});
		}
	}
});

function set_filters(frm) {
	// Set query filters
	frm.set_query('work_project', function() {
		return {
			filters: {
				status: ['not in', ['Completed', 'Cancelled']]
			}
		};
	});
	
	frm.set_query('task', function() {
		return {
			filters: {
				status: ['not in', ['Completed', 'Cancelled']]
			}
		};
	});
	
	frm.set_query('assigned_employee', function() {
		return {
			filters: {
				status: 'Active'
			}
		};
	});
}

function validate_repeat_dates(frm) {
	if (frm.doc.repeat_start_date && frm.doc.repeat_end_date) {
		if (frm.doc.repeat_start_date > frm.doc.repeat_end_date) {
			frappe.msgprint(__('반복 시작일은 종료일보다 이전이어야 합니다.'));
			frm.set_value('repeat_end_date', '');
		}
	}
}

function create_work_session(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Create Work Session'),
		fields: [
			{
				label: __('Execution Date'),
				fieldname: 'execution_date',
				fieldtype: 'Date',
				default: frappe.datetime.get_today(),
				reqd: 1
			}
		],
		primary_action_label: __('Create'),
		primary_action(values) {
			frappe.call({
				method: 'create_work_session',
				doc: frm.doc,
				args: {
					execution_date: values.execution_date
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint(__('Work Session {0} created successfully', [r.message]));
						frm.reload_doc();
					}
				}
			});
			d.hide();
		}
	});
	d.show();
}

function preview_schedule(frm) {
	frappe.call({
		method: 'get_next_execution_dates',
		doc: frm.doc,
		args: {
			count: 30
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				let dates_html = r.message.map(date => 
					`<li>${frappe.datetime.str_to_user(date)}</li>`
				).join('');
				
				frappe.msgprint({
					title: __('Next 30 Execution Dates'),
					message: `<ul>${dates_html}</ul>`,
					wide: true
				});
			} else {
				frappe.msgprint(__('No execution dates found'));
			}
		}
	});
}
