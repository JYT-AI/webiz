import json
import frappe

@frappe.whitelist()
def get_task_assignments(task_name=None, project=None, status=None, assigned_to=None):
	"""
	Task 할당 정보를 조회하는 함수

	Args:
		task_name (str, optional): 특정 Task 이름
		project (str, optional): 프로젝트 필터
		status (str, optional): Task 상태 필터 (Open, Working, Completed 등)
		assigned_to (str, optional): 할당된 사용자 필터

	Returns:
		list: Task 할당 정보 리스트
	"""
	# 기본 필터 설정
	filters = {}

	if task_name:
		filters["name"] = task_name
	if project:
		filters["project"] = project
	if status:
		filters["status"] = status

	# Task 기본 정보 조회
	task_fields = [
		"name",
		"subject",
		"status",
		"priority",
		"project",
		"exp_start_date",
		"exp_end_date",
		"progress",
		"_assign"
	]

	tasks = frappe.get_all("Task", filters=filters, fields=task_fields)

	result = []
	for task in tasks:
		# _assign 필드에서 할당된 사용자 정보 파싱
		assigned_users = []
		if task.get("_assign"):
			try:
				assigned_users = json.loads(task["_assign"])
			except (json.JSONDecodeError, TypeError):
				assigned_users = []

		# assigned_to 필터가 있는 경우 해당 사용자가 할당된 Task만 포함
		if assigned_to and assigned_to not in assigned_users:
			continue

		# ToDo 테이블에서 상세 할당 정보 조회
		assignment_details = []
		if assigned_users:
			todo_filters = {
				"reference_type": "Task",
				"reference_name": task["name"],
				"status": ("not in", ("Cancelled", "Closed")),
				"allocated_to": ("in", assigned_users)
			}

			todos = frappe.get_all(
				"ToDo",
				filters=todo_filters,
				fields=[
					"allocated_to",
					"assigned_by",
					"date",
					"priority",
					"description",
					"status",
					"creation"
				]
			)

			for todo in todos:
				assignment_details.append({
					"assigned_to": todo["allocated_to"],
					"assigned_by": todo["assigned_by"],
					"assignment_date": todo["date"],
					"assignment_priority": todo["priority"],
					"assignment_description": todo["description"],
					"assignment_status": todo["status"],
					"assigned_on": todo["creation"]
				})

		task_info = {
			"task_name": task["name"],
			"task_subject": task["subject"],
			"task_status": task["status"],
			"task_priority": task["priority"],
			"project": task["project"],
			"expected_start_date": task["exp_start_date"],
			"expected_end_date": task["exp_end_date"],
			"progress": task["progress"],
			"assigned_users": assigned_users,
			"assignment_details": assignment_details,
			"total_assignments": len(assigned_users)
		}

		result.append(task_info)

	return result