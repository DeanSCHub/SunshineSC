import { IInputs, IOutputs } from "./generated/ManifestTypes";
import { MAP_HTML } from "./generated/map";

/**
 * The Mantis map (one self-contained page) runs in an iframe so its full-page styles can't
 * touch the app around it. The two sides talk with postMessage:
 *   app -> map  { type: "mantis:select", id }
 *   app -> map  { type: "mantis:edits", list } / { type: "mantis:editmode", on }
 *   map -> app  { type: "mantis:selected", id, kind } / { type: "mantis:closed" } / { type: "mantis:open", url }
 *               { type: "mantis:edit", op, id, kind, asset, data }
 */
export class MantisMap implements ComponentFramework.StandardControl<IInputs, IOutputs> {
    private frame!: HTMLIFrameElement;
    private notify!: () => void;
    private ready = false;
    private pendingAsset = "";
    private lastAsset = "";
    private linkMode = "";
    private selected = "";
    private kind = "";
    private link = "";
    private uiK = 0;
    private editsJson: string | null = null;
    private editMode = false;
    private editOut = "";
    private onMessage = (e: MessageEvent) => this.receive(e);

    public init(context: ComponentFramework.Context<IInputs>, notifyOutputChanged: () => void, _state: ComponentFramework.Dictionary, container: HTMLDivElement): void {
        this.notify = notifyOutputChanged;
        context.mode.trackContainerResize(true);
        container.style.position = "relative";
        container.style.overflow = "hidden";
        this.frame = document.createElement("iframe");
        this.frame.title = "Mantis map";
        this.frame.style.cssText = "border:0;display:block;width:100%;height:100%";
        this.frame.addEventListener("load", () => {
            this.ready = true;
            this.uiK = 0;
            this.syncScale();
            this.sendEdits();
            if (this.pendingAsset) this.post(this.pendingAsset);
        });
        container.appendChild(this.frame);
        window.addEventListener("message", this.onMessage);
    }

    public updateView(context: ComponentFramework.Context<IInputs>): void {
        const w = context.mode.allocatedWidth, h = context.mode.allocatedHeight;
        if (w > 0) this.frame.style.width = `${w}px`;
        if (h > 0) this.frame.style.height = `${h}px`;

        // (re)load the page when it's first shown or the link mode changes
        const mode = context.parameters.LinkHandling.raw === "App" ? "app" : "browser";
        if (mode !== this.linkMode) {
            this.linkMode = mode;
            this.ready = false;
            const cfg = `<script>window.MANTIS_EMBED=${JSON.stringify({ links: mode })};</script>`;
            this.frame.srcdoc = MAP_HTML.replace("<head>", "<head>" + cfg);
        }

        // the player may have shrunk the whole app to fit the screen; let it settle, then measure
        setTimeout(() => this.syncScale(), 50);

        // edits: re-send only when the app's list or the edit switch actually changes
        const edits = context.parameters.Edits.raw || "";
        const editMode = context.parameters.EditMode.raw === true;
        if (edits !== this.editsJson || editMode !== this.editMode) {
            this.editsJson = edits;
            this.editMode = editMode;
            this.sendEdits();
        }

        const asset = (context.parameters.Asset.raw || "").trim();
        if (asset !== this.lastAsset) {
            this.lastAsset = asset;
            if (asset && this.ready) this.post(asset);
            else if (asset) this.pendingAsset = asset;
        }
    }

    public getOutputs(): IOutputs {
        const out: IOutputs = { SelectedAsset: this.selected, SelectedKind: this.kind, LinkToOpen: this.link, EditOut: this.editOut };
        // hand a link or an edit out once, then clear it, so the same thing twice still fires OnChange
        if (this.link || this.editOut) {
            this.link = "";
            this.editOut = "";
            setTimeout(() => this.notify(), 0);
        }
        return out;
    }

    public destroy(): void {
        window.removeEventListener("message", this.onMessage);
    }

    /**
     * A 16:9 app on an iPad is shown at about 86% size, which shrinks the map's buttons and text with it.
     * Measure how much the player has scaled us and ask the map to enlarge its controls to make up for it.
     */
    private syncScale(): void {
        if (!this.ready || !this.frame.offsetWidth) return;
        const shown = this.frame.getBoundingClientRect().width / this.frame.offsetWidth;
        const k = shown > 0 && shown < 0.98 ? Math.min(1.4, 1 / shown) : 1;
        if (Math.abs(k - this.uiK) < 0.02) return;
        this.uiK = k;
        this.frame.contentWindow?.postMessage({ type: "mantis:ui", k }, "*");
    }

    private sendEdits(): void {
        if (!this.ready) return;
        let list: unknown[] = [];
        try {
            const v = JSON.parse(this.editsJson || "[]");
            if (Array.isArray(v)) list = v;
        } catch {
            list = [];
        }
        this.frame.contentWindow?.postMessage({ type: "mantis:edits", list }, "*");
        this.frame.contentWindow?.postMessage({ type: "mantis:editmode", on: this.editMode }, "*");
    }

    private post(id: string): void {
        this.pendingAsset = "";
        this.frame.contentWindow?.postMessage({ type: "mantis:select", id }, "*");
    }

    private receive(e: MessageEvent): void {
        if (e.source !== this.frame.contentWindow) return;
        const d = e.data || {};
        if (d.type === "mantis:selected") {
            this.selected = String(d.id || "");
            this.kind = String(d.kind || "");
        } else if (d.type === "mantis:closed") {
            this.selected = "";
            this.kind = "";
        } else if (d.type === "mantis:open" && d.url) {
            this.link = String(d.url);
        } else if (d.type === "mantis:edit" && d.id) {
            this.editOut = JSON.stringify({ op: d.op, id: d.id, kind: d.kind || "", asset: d.asset || "", data: d.data || "" });
        } else {
            return;
        }
        this.notify();
    }
}
