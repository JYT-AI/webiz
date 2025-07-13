// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Session', {
	refresh: function(frm) {
		// Add custom buttons based on status
		add_custom_buttons(frm);
		
		// Set filters
		set_filters(frm);
		
		// Show status indicators
		show_status_indicators(frm);
		
		// Auto-refresh for mobile users
		if (frappe.is_mobile()) {
			setup_mobile_interface(frm);
		}
	},
	
	work_task: function(frm) {
		// Auto-fetch work task details
		if (frm.doc.work_task) {
			frappe.db.get_doc('Work Task', frm.doc.work_task).then(doc => {
				frm.set_value('work_project', doc.work_project);
				frm.set_value('customer_site', doc.customer_site);
				frm.set_value('checklist_template', doc.checklist_template);
				frm.set_value('assigned_employee', doc.assigned_employee);
				frm.set_value('estimated_duration', doc.estimated_duration);
				frm.set_value('description', doc.description);
				frm.set_value('special_instructions', doc.special_instructions);
			});
		}
	},
	
	actual_start_time: function(frm) {
		validate_times(frm);
	},
	
	actual_end_time: function(frm) {
		validate_times(frm);
		calculate_duration(frm);
	},
	
	break_duration: function(frm) {
		calculate_billable_hours(frm);
	}
});

// Checklist Results child table events
frappe.ui.form.on('Timesheet Checklist Result', {
	status: function(frm, cdt, cdn) {
		update_completion_progress(frm);
	}
});

function add_custom_buttons(frm) {
	// Clear existing custom buttons
	frm.clear_custom_buttons();
	
	if (frm.doc.status === 'Scheduled') {
		frm.add_custom_button(__('Start Work'), function() {
			start_work_session(frm);
		}, __('Actions')).addClass('btn-primary');
		
		frm.add_custom_button(__('Cancel'), function() {
			cancel_work_session(frm);
		}, __('Actions'));
	}
	
	if (frm.doc.status === 'In Progress') {
		frm.add_custom_button(__('Complete Work'), function() {
			complete_work_session(frm);
		}, __('Actions')).addClass('btn-success');
		
		frm.add_custom_button(__('Take Break'), function() {
			take_break(frm);
		}, __('Actions'));
	}
	
	if (frm.doc.status === 'Completed') {
		frm.add_custom_button(__('View Timesheet'), function() {
			if (frm.doc.timesheet) {
				frappe.set_route('Form', 'Timesheet', frm.doc.timesheet);
			}
		});
		
		frm.add_custom_button(__('Generate Report'), function() {
			generate_completion_report(frm);
		});
	}
	
	// Always available buttons
	frm.add_custom_button(__('View on Map'), function() {
		view_location_on_map(frm);
	}, __('Tools'));
	
	if (frm.doc.checklist_template) {
		frm.add_custom_button(__('Reload Checklist'), function() {
			reload_checklist_items(frm);
		}, __('Tools'));
	}
}

function set_filters(frm) {
	// Set query filters
	frm.set_query('work_task', function() {
		return {
			filters: {
				is_template: 1,
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

function show_status_indicators(frm) {
	// Clear existing indicators
	frm.dashboard.clear_indicators();
	
	// Status indicator
	let status_color = get_status_color(frm.doc.status);
	frm.dashboard.add_indicator(__(frm.doc.status), status_color);
	
	// Completion percentage
	if (frm.doc.checklist_results && frm.doc.checklist_results.length > 0) {
		let completion = calculate_completion_percentage(frm);
		frm.dashboard.add_indicator(__('Completion: {0}%', [completion]), 
			completion === 100 ? 'green' : 'orange');
	}
	
	// Time tracking
	if (frm.doc.actual_duration) {
		frm.dashboard.add_indicator(__('Duration: {0}h', [frm.doc.actual_duration.toFixed(1)]), 'blue');
	}
}

function setup_mobile_interface(frm) {
	// Add mobile-specific styling and functionality
	if (frm.doc.status === 'In Progress') {
		// Add quick checklist update buttons
		add_quick_checklist_buttons(frm);
	}
}

function start_work_session(frm) {
	if (navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(function(position) {
			let location = `${position.coords.latitude},${position.coords.longitude}`;
			
			frappe.call({
				method: 'start_work',
				doc: frm.doc,
				args: {
					check_in_location: location
				},
				callback: function(r) {
					frm.reload_doc();
				}
			});
		}, function(error) {
			// Start without location if GPS fails
			frappe.call({
				method: 'start_work',
				doc: frm.doc,
				callback: function(r) {
					frm.reload_doc();
				}
			});
		});
	} else {
		frappe.call({
			method: 'start_work',
			doc: frm.doc,
			callback: function(r) {
				frm.reload_doc();
			}
		});
	}
}

function complete_work_session(frm) {
	// Check mandatory checklist items
	let mandatory_incomplete = frm.doc.checklist_results.filter(item => 
		item.is_mandatory && item.status !== 'Completed'
	);
	
	if (mandatory_incomplete.length > 0) {
		frappe.msgprint({
			title: __('Incomplete Mandatory Items'),
			message: __('다음 필수 항목들을 완료해야 합니다:<br>') + 
				mandatory_incomplete.map(item => `• ${item.checklist_item}`).join('<br>'),
			indicator: 'red'
		});
		return;
	}
	
	if (navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(function(position) {
			let location = `${position.coords.latitude},${position.coords.longitude}`;
			
			frappe.call({
				method: 'complete_work',
				doc: frm.doc,
				args: {
					check_out_location: location
				},
				callback: function(r) {
					frm.reload_doc();
				}
			});
		}, function(error) {
			// Complete without location if GPS fails
			frappe.call({
				method: 'complete_work',
				doc: frm.doc,
				callback: function(r) {
					frm.reload_doc();
				}
			});
		});
	} else {
		frappe.call({
			method: 'complete_work',
			doc: frm.doc,
			callback: function(r) {
				frm.reload_doc();
			}
		});
	}
}

function cancel_work_session(frm) {
	frappe.confirm(__('작업을 취소하시겠습니까?'), function() {
		frm.set_value('status', 'Cancelled');
		frm.save();
	});
}

function validate_times(frm) {
	if (frm.doc.actual_start_time && frm.doc.actual_end_time) {
		if (frm.doc.actual_start_time >= frm.doc.actual_end_time) {
			frappe.msgprint(__('실제 시작 시간은 종료 시간보다 이전이어야 합니다.'));
			frm.set_value('actual_end_time', '');
		}
	}
}

function calculate_duration(frm) {
	if (frm.doc.actual_start_time && frm.doc.actual_end_time) {
		let start = new Date(frm.doc.actual_start_time);
		let end = new Date(frm.doc.actual_end_time);
		let duration = (end - start) / (1000 * 60 * 60); // Convert to hours
		
		frm.set_value('actual_duration', duration);
		calculate_billable_hours(frm);
	}
}

function calculate_billable_hours(frm) {
	if (frm.doc.actual_duration) {
		let billable = frm.doc.actual_duration - (frm.doc.break_duration || 0);
		frm.set_value('total_billable_hours', billable);
		
		// Calculate overtime
		if (frm.doc.estimated_duration && frm.doc.actual_duration > frm.doc.estimated_duration) {
			frm.set_value('overtime_hours', frm.doc.actual_duration - frm.doc.estimated_duration);
		}
	}
}

function calculate_completion_percentage(frm) {
	if (!frm.doc.checklist_results || frm.doc.checklist_results.length === 0) {
		return 0;
	}
	
	let total = frm.doc.checklist_results.length;
	let completed = frm.doc.checklist_results.filter(item => item.status === 'Completed').length;
	
	return Math.round((completed / total) * 100);
}

function update_completion_progress(frm) {
	// Update progress indicator
	show_status_indicators(frm);
}

function get_status_color(status) {
	const status_colors = {
		'Scheduled': 'blue',
		'In Progress': 'orange',
		'Completed': 'green',
		'Cancelled': 'red',
		'On Hold': 'yellow',
		'Overdue': 'red'
	};
	return status_colors[status] || 'gray';
}

function view_location_on_map(frm) {
	if (frm.doc.customer_site) {
		frappe.db.get_value('Customer Site', frm.doc.customer_site, ['latitude', 'longitude'])
			.then(r => {
				if (r.message && r.message.latitude && r.message.longitude) {
					let url = `https://maps.google.com/maps?q=${r.message.latitude},${r.message.longitude}`;
					window.open(url, '_blank');
				} else {
					frappe.msgprint(__('위치 정보가 없습니다.'));
				}
			});
	}
}

function reload_checklist_items(frm) {
	frappe.confirm(__('기존 체크리스트 결과가 삭제됩니다. 계속하시겠습니까?'), function() {
		frm.clear_table('checklist_results');
		frm.save().then(() => {
			frm.reload_doc();
		});
	});
}

function generate_completion_report(frm) {
	frappe.call({
		method: 'get_mobile_view_data',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				show_completion_report(r.message);
			}
		}
	});
}

function show_completion_report(data) {
	let report_html = `
		<div class="completion-report">
			<h4>${data.session_info.title}</h4>
			<p><strong>Date:</strong> ${frappe.datetime.str_to_user(data.session_info.work_date)}</p>
			<p><strong>Site:</strong> ${data.session_info.site_name}</p>
			<p><strong>Completion:</strong> ${data.completion_percentage}%</p>
			
			<h5>Checklist Results:</h5>
			<table class="table table-bordered">
				<thead>
					<tr><th>Item</th><th>Status</th><th>Notes</th></tr>
				</thead>
				<tbody>
	`;
	
	data.checklist.forEach(item => {
		let status_badge = item.status === 'Completed' ? 
			'<span class="badge badge-success">Completed</span>' :
			'<span class="badge badge-warning">' + item.status + '</span>';
		
		report_html += `
			<tr>
				<td>${item.item}</td>
				<td>${status_badge}</td>
				<td>${item.notes || '-'}</td>
			</tr>
		`;
	});
	
	report_html += `
				</tbody>
			</table>
		</div>
	`;
	
	frappe.msgprint({
		title: __('Completion Report'),
		message: report_html,
		wide: true
	});
}
