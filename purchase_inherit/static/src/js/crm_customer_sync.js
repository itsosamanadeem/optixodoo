/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CrmCustomerSync extends Component {
    static template = "purchase_inherit.CrmCustomerSync";
    static props = ["*"];
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ job: null, connectionError: false });
        this.stopped = false;
        onWillStart(() => this.poll());
        onWillUnmount(() => {
            this.stopped = true;
            clearTimeout(this.timer);
        });
    }
    async poll() {
        try {
            const [job] = await this.orm.read("optix.crm.customer.sync",
                [this.props.action.params.job_id],
                ["state", "processed", "total", "created", "updated", "error"]);
            if (this.stopped) { return; }
            this.state.job = job;
            this.state.connectionError = false;
        } catch {
            if (this.stopped) { return; }
            this.state.connectionError = true;
        }
        if (!this.stopped && (!this.state.job || this.state.job.state === "running" || this.state.connectionError)) {
            this.timer = setTimeout(() => this.poll(), 3000);
        }
    }
    get percentage() {
        const job = this.state.job;
        return job?.total ? Math.min(100, Math.round(job.processed * 100 / job.total)) : 0;
    }
    async back() {
        await this.action.doAction({ type: "ir.actions.act_window", res_model: "stock.picking",
            res_id: this.props.action.params.picking_id, views: [[false, "form"]], target: "current" });
    }
}
registry.category("actions").add("optix_crm_customer_sync", CrmCustomerSync);
