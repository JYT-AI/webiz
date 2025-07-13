// Copyright (c) 2025, JYT AI and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Attendance', {
	refresh: function(frm) {
		// Add custom buttons
		add_custom_buttons(frm);
		
		// Set filters
		set_filters(frm);
		
		// Show status indicators
		show_status_indicators(frm);
		
		// Setup mobile interface
		if (frappe.is_mobile()) {
			setup_mobile_interface(frm);
		}
	},
	
	employee: function(frm) {
		// Auto-fetch employee details
		if (frm.doc.employee) {
			frappe.db.get_value('Employee', frm.doc.employee, 'employee_name')
				.then(r => {
					if (r.message) {
						frm.set_value('employee_name', r.message.employee_name);
					}
				});
		}
	},
	
	work_site: function(frm) {
		// Auto-set verification method to GPS when work site is selected
		if (frm.doc.work_site && !frm.doc.verification_method) {
			frm.set_value('verification_method', 'GPS');
		}
	},
	
	in_time: function(frm) {
		validate_times(frm);
	},
	
	out_time: function(frm) {
		validate_times(frm);
		calculate_working_hours(frm);
	},
	
	break_hours: function(frm) {
		calculate_working_hours(frm);
	}
});

function add_custom_buttons(frm) {
	// Clear existing custom buttons
	frm.clear_custom_buttons();
	
	if (!frm.doc.in_time) {
		frm.add_custom_button(__('Check In'), function() {
			check_in_employee(frm);
		}, __('Actions')).addClass('btn-primary');
	}
	
	if (frm.doc.in_time && !frm.doc.out_time) {
		frm.add_custom_button(__('Check Out'), function() {
			check_out_employee(frm);
		}, __('Actions')).addClass('btn-success');
	}
	
	if (frm.doc.work_site) {
		frm.add_custom_button(__('View Site Location'), function() {
			view_site_location(frm);
		}, __('Tools'));
	}
	
	if (frm.doc.check_in_location || frm.doc.check_out_location) {
		frm.add_custom_button(__('View Check-in Location'), function() {
			view_checkin_location(frm);
		}, __('Tools'));
	}
	
	frm.add_custom_button(__('Generate Report'), function() {
		generate_attendance_report(frm);
	}, __('Reports'));
}

function set_filters(frm) {
	// Set query filters
	frm.set_query('employee', function() {
		return {
			filters: {
				status: 'Active'
			}
		};
	});
	
	frm.set_query('work_session', function() {
		return {
			filters: {
				assigned_employee: frm.doc.employee,
				work_date: frm.doc.attendance_date
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
	
	// Location verification indicator
	if (frm.doc.location_verified) {
		frm.dashboard.add_indicator(__('Location Verified'), 'green');
	} else if (frm.doc.check_in_location) {
		frm.dashboard.add_indicator(__('Location Not Verified'), 'red');
	}
	
	// Working hours indicator
	if (frm.doc.total_working_hours) {
		frm.dashboard.add_indicator(__('Hours: {0}', [frm.doc.total_working_hours.toFixed(1)]), 'blue');
	}
	
	// Attendance score indicator
	if (frm.doc.attendance_score) {
		let score_color = frm.doc.attendance_score >= 80 ? 'green' : 
						  frm.doc.attendance_score >= 60 ? 'orange' : 'red';
		frm.dashboard.add_indicator(__('Score: {0}', [frm.doc.attendance_score]), score_color);
	}
}

function setup_mobile_interface(frm) {
	// Add mobile-specific functionality
	if (!frm.doc.in_time || !frm.doc.out_time) {
		add_quick_action_buttons(frm);
	}
}

function check_in_employee(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Check In'),
		fields: [
			{
				label: __('Take Photo'),
				fieldname: 'take_photo',
				fieldtype: 'Button',
				click: function() {
					take_photo('check_in');
				}
			},
			{
				label: __('Photo'),
				fieldname: 'photo',
				fieldtype: 'Attach'
			},
			{
				label: __('Notes'),
				fieldname: 'notes',
				fieldtype: 'Text'
			}
		],
		primary_action_label: __('Check In'),
		primary_action(values) {
			if (navigator.geolocation) {
				navigator.geolocation.getCurrentPosition(function(position) {
					let location = `${position.coords.latitude},${position.coords.longitude}`;
					let device_info = get_device_info();
					
					frappe.call({
						method: 'check_in',
						doc: frm.doc,
						args: {
							location: location,
							photo: values.photo,
							device_info: device_info
						},
						callback: function(r) {
							if (r.message) {
								frappe.msgprint(r.message);
								frm.reload_doc();
							}
						}
					});
				}, function(error) {
					frappe.msgprint(__('GPS 위치를 가져올 수 없습니다. 수동으로 체크인합니다.'));
					manual_check_in(frm, values);
				});
			} else {
				manual_check_in(frm, values);
			}
			d.hide();
		}
	});
	d.show();
}

function check_out_employee(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Check Out'),
		fields: [
			{
				label: __('Take Photo'),
				fieldname: 'take_photo',
				fieldtype: 'Button',
				click: function() {
					take_photo('check_out');
				}
			},
			{
				label: __('Photo'),
				fieldname: 'photo',
				fieldtype: 'Attach'
			},
			{
				label: __('Notes'),
				fieldname: 'notes',
				fieldtype: 'Text'
			}
		],
		primary_action_label: __('Check Out'),
		primary_action(values) {
			if (navigator.geolocation) {
				navigator.geolocation.getCurrentPosition(function(position) {
					let location = `${position.coords.latitude},${position.coords.longitude}`;
					
					frappe.call({
						method: 'check_out',
						doc: frm.doc,
						args: {
							location: location,
							photo: values.photo
						},
						callback: function(r) {
							if (r.message) {
								frappe.msgprint(r.message);
								frm.reload_doc();
							}
						}
					});
				}, function(error) {
					frappe.msgprint(__('GPS 위치를 가져올 수 없습니다. 수동으로 체크아웃합니다.'));
					manual_check_out(frm, values);
				});
			} else {
				manual_check_out(frm, values);
			}
			d.hide();
		}
	});
	d.show();
}

function manual_check_in(frm, values) {
	frappe.call({
		method: 'check_in',
		doc: frm.doc,
		args: {
			photo: values.photo,
			device_info: get_device_info()
		},
		callback: function(r) {
			if (r.message) {
				frappe.msgprint(r.message);
				frm.reload_doc();
			}
		}
	});
}

function manual_check_out(frm, values) {
	frappe.call({
		method: 'check_out',
		doc: frm.doc,
		args: {
			photo: values.photo
		},
		callback: function(r) {
			if (r.message) {
				frappe.msgprint(r.message);
				frm.reload_doc();
			}
		}
	});
}

function validate_times(frm) {
	if (frm.doc.in_time && frm.doc.out_time) {
		if (frm.doc.in_time >= frm.doc.out_time) {
			frappe.msgprint(__('체크인 시간은 체크아웃 시간보다 이전이어야 합니다.'));
			frm.set_value('out_time', '');
		}
	}
}

function calculate_working_hours(frm) {
	if (frm.doc.in_time && frm.doc.out_time) {
		let in_time = new Date(frm.doc.in_time);
		let out_time = new Date(frm.doc.out_time);
		let total_hours = (out_time - in_time) / (1000 * 60 * 60);
		
		let working_hours = total_hours - (frm.doc.break_hours || 0);
		frm.set_value('total_working_hours', working_hours);
		
		// Calculate overtime (assuming 8 hours standard)
		if (working_hours > 8) {
			frm.set_value('overtime_hours', working_hours - 8);
		}
	}
}

function get_status_color(status) {
	const status_colors = {
		'Present': 'green',
		'Absent': 'red',
		'Half Day': 'orange',
		'On Leave': 'blue',
		'Work From Home': 'purple'
	};
	return status_colors[status] || 'gray';
}

function get_device_info() {
	return `${navigator.userAgent} | ${screen.width}x${screen.height}`;
}

function take_photo(type) {
	// This would integrate with camera API in a real mobile app
	frappe.msgprint(__('Camera integration would be implemented here for mobile app'));
}

function view_site_location(frm) {
	if (frm.doc.work_site) {
		frappe.db.get_value('Customer Site', frm.doc.work_site, ['latitude', 'longitude', 'site_name'])
			.then(r => {
				if (r.message && r.message.latitude && r.message.longitude) {
					let url = `https://maps.google.com/maps?q=${r.message.latitude},${r.message.longitude}`;
					window.open(url, '_blank');
				} else {
					frappe.msgprint(__('현장 위치 정보가 없습니다.'));
				}
			});
	}
}

function view_checkin_location(frm) {
	if (frm.doc.check_in_location) {
		let coords = frm.doc.check_in_location.split(',');
		if (coords.length === 2) {
			let url = `https://maps.google.com/maps?q=${coords[0]},${coords[1]}`;
			window.open(url, '_blank');
		}
	}
}

function generate_attendance_report(frm) {
	frappe.call({
		method: 'get_mobile_summary',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				show_attendance_report(r.message);
			}
		}
	});
}

function show_attendance_report(data) {
	let report_html = `
		<div class="attendance-report">
			<h4>Attendance Report</h4>
			<table class="table table-bordered">
				<tr><td><strong>Employee:</strong></td><td>${data.employee_name}</td></tr>
				<tr><td><strong>Date:</strong></td><td>${frappe.datetime.str_to_user(data.date)}</td></tr>
				<tr><td><strong>Status:</strong></td><td>${data.status}</td></tr>
				<tr><td><strong>Check In:</strong></td><td>${data.in_time ? frappe.datetime.str_to_user(data.in_time) : '-'}</td></tr>
				<tr><td><strong>Check Out:</strong></td><td>${data.out_time ? frappe.datetime.str_to_user(data.out_time) : '-'}</td></tr>
				<tr><td><strong>Total Hours:</strong></td><td>${data.total_hours ? data.total_hours.toFixed(1) + 'h' : '-'}</td></tr>
				<tr><td><strong>Location Status:</strong></td><td>${data.location_status}</td></tr>
				<tr><td><strong>Attendance Score:</strong></td><td>${data.attendance_score}/100</td></tr>
				<tr><td><strong>Work Site:</strong></td><td>${data.site_name || '-'}</td></tr>
			</table>
		</div>
	`;
	
	frappe.msgprint({
		title: __('Attendance Report'),
		message: report_html,
		wide: true
	});
}
