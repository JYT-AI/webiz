// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Project', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Create Work Tasks'), function() {
				frappe.new_doc('Work Task', {
					work_project: frm.doc.name,
					project: frm.doc.project,
					customer: frm.doc.customer
				});
			});
		}
		
		// Set filters
		frm.set_query('project', function() {
			return {
				filters: {
					status: ['not in', ['Completed', 'Cancelled']]
				}
			};
		});
	},
	
	project: function(frm) {
		// Auto-fetch project details when project is selected
		if (frm.doc.project) {
			frappe.db.get_doc('Project', frm.doc.project).then(doc => {
				frm.set_value('project_name', doc.project_name);
				frm.set_value('customer', doc.customer);
				frm.set_value('expected_start_date', doc.expected_start_date);
				frm.set_value('expected_end_date', doc.expected_end_date);
			});
		}
	},
	
	contract_start_date: function(frm) {
		// Validate contract dates
		if (frm.doc.contract_start_date && frm.doc.contract_end_date) {
			if (frm.doc.contract_start_date > frm.doc.contract_end_date) {
				frappe.msgprint(__('계약 시작일은 종료일보다 이전이어야 합니다.'));
				frm.set_value('contract_start_date', '');
			}
		}
	},
	
	contract_end_date: function(frm) {
		// Validate contract dates
		if (frm.doc.contract_start_date && frm.doc.contract_end_date) {
			if (frm.doc.contract_start_date > frm.doc.contract_end_date) {
				frappe.msgprint(__('계약 종료일은 시작일보다 이후여야 합니다.'));
				frm.set_value('contract_end_date', '');
			}
		}
	},
	
	monthly_contract_amount: function(frm) {
		// Calculate total contract amount if billing cycle is monthly
		if (frm.doc.monthly_contract_amount && frm.doc.billing_cycle === '월간') {
			calculate_total_amount(frm);
		}
	},
	
	billing_cycle: function(frm) {
		// Calculate total contract amount based on billing cycle
		if (frm.doc.monthly_contract_amount) {
			calculate_total_amount(frm);
		}
	}
});

function calculate_total_amount(frm) {
	if (frm.doc.contract_start_date && frm.doc.contract_end_date && frm.doc.monthly_contract_amount) {
		let start_date = new Date(frm.doc.contract_start_date);
		let end_date = new Date(frm.doc.contract_end_date);
		let months = (end_date.getFullYear() - start_date.getFullYear()) * 12 + 
					 (end_date.getMonth() - start_date.getMonth()) + 1;
		
		if (frm.doc.billing_cycle === '월간') {
			frm.set_value('total_contract_amount', frm.doc.monthly_contract_amount * months);
		}
	}
}
