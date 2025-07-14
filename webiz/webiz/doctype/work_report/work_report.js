// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Report', {
    refresh: function(frm) {
        // Add custom buttons based on status
        if (frm.doc.status === "Draft" && !frm.is_new()) {
            frm.add_custom_button(__('Submit Report'), function() {
                frm.set_value('status', 'Submitted');
                frm.save();
            }).addClass('btn-primary');
        }
        
        if (frm.doc.status === "Submitted" && frappe.user.has_role("Projects Manager")) {
            frm.add_custom_button(__('Approve'), function() {
                frm.set_value('status', 'Approved');
                frm.save().then(() => {
                    frm.submit();
                });
            }).addClass('btn-success');
            
            frm.add_custom_button(__('Reject'), function() {
                frm.set_value('status', 'Rejected');
                frm.save();
            }).addClass('btn-danger');
        }
    },
    
    task: function(frm) {
        // Auto-fill customer site from task
        if (frm.doc.task) {
            frappe.db.get_value('Task', frm.doc.task, ['custom_customer_site', 'exp_start_date', 'exp_end_date'])
                .then(r => {
                    if (r.message && r.message.custom_customer_site) {
                        frm.set_value('customer_site', r.message.custom_customer_site);
                    }
                    
                    // Set default start time from task schedule
                    if (r.message && r.message.exp_start_date && !frm.doc.actual_start_time) {
                        frm.set_value('actual_start_time', r.message.exp_start_date);
                    }
                    
                    if (r.message && r.message.exp_end_date && !frm.doc.actual_end_time) {
                        frm.set_value('actual_end_time', r.message.exp_end_date);
                    }
                });
        }
    },
    
    actual_start_time: function(frm) {
        calculate_hours(frm);
    },
    
    actual_end_time: function(frm) {
        calculate_hours(frm);
    }
});

function calculate_hours(frm) {
    if (frm.doc.actual_start_time && frm.doc.actual_end_time) {
        let start = new Date(frm.doc.actual_start_time);
        let end = new Date(frm.doc.actual_end_time);
        
        if (end > start) {
            let hours = (end - start) / (1000 * 60 * 60);
            frm.set_value('total_hours', hours.toFixed(2));
        }
    }
}
