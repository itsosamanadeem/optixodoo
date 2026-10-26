from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _check_project_approved_for_tasks(self):
        for task in self:
            project = task.project_id
            if project and project.approval_state != "approved":
                raise ValidationError(
                    _(
                        "You can only create tasks for approved projects. "
                        "Project '%(project)s' is currently '%(state)s'."
                    )
                    % {
                        "project": project.display_name,
                        "state": dict(project._fields["approval_state"].selection).get(
                            project.approval_state,
                            project.approval_state,
                        ),
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._check_project_approved_for_tasks()
        return tasks

    def write(self, vals):
        res = super().write(vals)
        if "project_id" in vals:
            self._check_project_approved_for_tasks()
        return res
