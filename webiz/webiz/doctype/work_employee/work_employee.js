// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Employee', {
	refresh: function(frm) {
		// Add custom buttons
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('View Schedule'), function() {
				view_employee_schedule(frm);
			});
			
			frm.add_custom_button(__('View Work Sessions'), function() {
				frappe.set_route('List', 'Work Session', {
					assigned_employee: frm.doc.employee
				});
			});
			
			frm.add_custom_button(__('Performance Report'), function() {
				show_performance_report(frm);
			});
		}
		
		// Set filters
		set_filters(frm);
		
		// Show status indicators
		if (frm.doc.status === 'Active') {
			frm.dashboard.add_indicator(__('Active'), 'green');
		} else {
			frm.dashboard.add_indicator(__(frm.doc.status), 'red');
		}
		
		// Show workload indicator
		if (frm.doc.current_workload > 0) {
			frm.dashboard.add_indicator(__('Workload: {0}', [frm.doc.current_workload]), 'orange');
		}
	},
	
	employee: function(frm) {
		// Auto-fetch employee details when employee is selected
		if (frm.doc.employee) {
			frappe.db.get_doc('Employee', frm.doc.employee).then(doc => {
				frm.set_value('employee_name', doc.employee_name);
				frm.set_value('department', doc.department);
				frm.set_value('designation', doc.designation);
				frm.set_value('date_of_joining', doc.date_of_joining);
				frm.set_value('mobile_no', doc.cell_number);
				frm.set_value('email', doc.company_email);
			});
		}
	},
	
	max_hours_per_day: function(frm) {
		// Validate max hours per day
		if (frm.doc.max_hours_per_day > 24) {
			frappe.msgprint(__('일일 최대 근무시간은 24시간을 초과할 수 없습니다.'));
			frm.set_value('max_hours_per_day', 8);
		}
		if (frm.doc.max_hours_per_day < 0) {
			frappe.msgprint(__('일일 최대 근무시간은 0보다 커야 합니다.'));
			frm.set_value('max_hours_per_day', 8);
		}
	}
});

function set_filters(frm) {
	// Set query filters
	frm.set_query('employee', function() {
		return {
			filters: {
				status: 'Active'
			}
		};
	});
}

function view_employee_schedule(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Employee Schedule'),
		fields: [
			{
				label: __('Start Date'),
				fieldname: 'start_date',
				fieldtype: 'Date',
				default: frappe.datetime.get_today(),
				reqd: 1
			},
			{
				label: __('End Date'),
				fieldname: 'end_date',
				fieldtype: 'Date',
				default: frappe.datetime.add_days(frappe.datetime.get_today(), 7),
				reqd: 1
			}
		],
		primary_action_label: __('View Schedule'),
		primary_action(values) {
			frappe.call({
				method: 'get_schedule',
				doc: frm.doc,
				args: {
					start_date: values.start_date,
					end_date: values.end_date
				},
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						show_schedule_dialog(r.message, values.start_date, values.end_date);
					} else {
						frappe.msgprint(__('해당 기간에 예정된 작업이 없습니다.'));
					}
				}
			});
			d.hide();
		}
	});
	d.show();
}

function show_schedule_dialog(schedule, start_date, end_date) {
	let schedule_html = `
		<div class="schedule-container">
			<h4>Schedule: ${frappe.datetime.str_to_user(start_date)} - ${frappe.datetime.str_to_user(end_date)}</h4>
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>Date</th>
						<th>Time</th>
						<th>Site</th>
						<th>Task</th>
						<th>Duration</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
	`;
	
	schedule.forEach(item => {
		let status_color = get_status_color(item.status);
		schedule_html += `
			<tr>
				<td>${frappe.datetime.str_to_user(item.date)}</td>
				<td>${item.start_time ? frappe.datetime.str_to_user(item.start_time) : '-'}</td>
				<td>${item.site || '-'}</td>
				<td>${item.task || '-'}</td>
				<td>${item.duration ? item.duration + 'h' : '-'}</td>
				<td><span class="indicator ${status_color}">${item.status}</span></td>
			</tr>
		`;
	});
	
	schedule_html += `
				</tbody>
			</table>
		</div>
	`;
	
	frappe.msgprint({
		title: __('Employee Schedule'),
		message: schedule_html,
		wide: true
	});
}

function show_performance_report(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Performance Report'),
		fields: [
			{
				label: __('Start Date'),
				fieldname: 'start_date',
				fieldtype: 'Date',
				default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
				reqd: 1
			},
			{
				label: __('End Date'),
				fieldname: 'end_date',
				fieldtype: 'Date',
				default: frappe.datetime.get_today(),
				reqd: 1
			}
		],
		primary_action_label: __('Generate Report'),
		primary_action(values) {
			frappe.call({
				method: 'get_workload_for_period',
				doc: frm.doc,
				args: {
					start_date: values.start_date,
					end_date: values.end_date
				},
				callback: function(r) {
					if (r.message) {
						show_performance_dialog(r.message, values.start_date, values.end_date);
					}
				}
			});
			d.hide();
		}
	});
	d.show();
}

function show_performance_dialog(stats, start_date, end_date) {
	let performance_html = `
		<div class="performance-container">
			<h4>Performance Report: ${frappe.datetime.str_to_user(start_date)} - ${frappe.datetime.str_to_user(end_date)}</h4>
			<div class="row">
				<div class="col-md-6">
					<div class="card">
						<div class="card-body">
							<h5>Work Statistics</h5>
							<p><strong>Total Sessions:</strong> ${stats.total_sessions}</p>
							<p><strong>Completed Sessions:</strong> ${stats.completed_sessions}</p>
							<p><strong>Completion Rate:</strong> ${stats.total_sessions > 0 ? Math.round((stats.completed_sessions / stats.total_sessions) * 100) : 0}%</p>
							<p><strong>Total Hours:</strong> ${stats.total_hours.toFixed(1)}h</p>
						</div>
					</div>
				</div>
				<div class="col-md-6">
					<div class="card">
						<div class="card-body">
							<h5>Quality Rating</h5>
							<p><strong>Average Rating:</strong> ${stats.average_rating.toFixed(1)}/5</p>
							<div class="progress">
								<div class="progress-bar" style="width: ${(stats.average_rating / 5) * 100}%"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	frappe.msgprint({
		title: __('Performance Report'),
		message: performance_html,
		wide: true
	});
}

function get_status_color(status) {
	const status_colors = {
		'Scheduled': 'blue',
		'In Progress': 'orange',
		'Completed': 'green',
		'Cancelled': 'red',
		'On Hold': 'yellow'
	};
	return status_colors[status] || 'gray';
}
