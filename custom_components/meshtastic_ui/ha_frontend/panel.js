import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@4.1.1/lit-element.js?module";

const TABS = ["radio", "messages", "nodes", "stats"];
const TAB_LABELS = {
  radio: "Radio",
  messages: "Messages",
  nodes: "Nodes",
  stats: "Stats",
};
const TAB_ICONS = {
  radio: "mdi:radio-handheld",
  messages: "mdi:message-text",
  nodes: "mdi:access-point-network",
  stats: "mdi:chart-bar",
};

class MeshtasticUiPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _activeTab: { type: String },
      _gateways: { type: Array },
      _messages: { type: Object },
      _channels: { type: Array },
      _dms: { type: Array },
      _selectedConversation: { type: String },
      _nodes: { type: Object },
      _stats: { type: Object },
      _messageInput: { type: String },
      _sortColumn: { type: String },
      _sortAsc: { type: Boolean },
      _subscriptionId: { type: Number },
    };
  }

  constructor() {
    super();
    this._activeTab = "radio";
    this._gateways = [];
    this._messages = {};
    this._channels = [];
    this._dms = [];
    this._selectedConversation = "";
    this._nodes = {};
    this._stats = { messages_today: 0, active_nodes: 0, total_nodes: 0, channel_count: 0 };
    this._messageInput = "";
    this._sortColumn = "name";
    this._sortAsc = true;
    this._subscriptionId = null;
    this._wsConnection = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadData();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubscribe();
  }

  async _loadData() {
    await this._loadGateways();
    await this._loadMessages();
    await this._loadNodes();
    await this._loadStats();
    this._subscribe();
  }

  async _wsCommand(type, data = {}) {
    if (!this.hass) return null;
    try {
      return await this.hass.callWS({ type, ...data });
    } catch (err) {
      console.error(`WS command ${type} failed:`, err);
      return null;
    }
  }

  async _loadGateways() {
    const result = await this._wsCommand("meshtastic_ui/gateways");
    if (result) this._gateways = result.gateways || [];
  }

  async _loadMessages() {
    const result = await this._wsCommand("meshtastic_ui/messages");
    if (result) {
      this._messages = result.messages || {};
      this._channels = result.channels || [];
      this._dms = result.dms || [];
    }
  }

  async _loadNodes() {
    const result = await this._wsCommand("meshtastic_ui/nodes");
    if (result) this._nodes = result.nodes || {};
  }

  async _loadStats() {
    const result = await this._wsCommand("meshtastic_ui/stats");
    if (result) this._stats = result;
  }

  _subscribe() {
    if (!this.hass || this._subscriptionId) return;

    this.hass.connection.subscribeMessage(
      (event) => this._handleRealtimeMessage(event),
      { type: "meshtastic_ui/subscribe" }
    ).then((unsub) => {
      this._unsubscribeFn = unsub;
    }).catch((err) => {
      console.error("Failed to subscribe:", err);
    });
  }

  _unsubscribe() {
    if (this._unsubscribeFn) {
      this._unsubscribeFn();
      this._unsubscribeFn = null;
    }
  }

  _handleRealtimeMessage(data) {
    const key = data.type === "dm" ? data.partner : data.channel;
    if (!key) return;

    if (!this._messages[key]) {
      this._messages[key] = [];
      if (data.type === "dm" && !this._dms.includes(key)) {
        this._dms = [...this._dms, key];
      } else if (data.type === "channel" && !this._channels.includes(key)) {
        this._channels = [...this._channels, key];
      }
    }

    this._messages = {
      ...this._messages,
      [key]: [...(this._messages[key] || []), data],
    };

    this._stats = {
      ...this._stats,
      messages_today: (this._stats.messages_today || 0) + 1,
    };
  }

  _setTab(tab) {
    this._activeTab = tab;
    if (tab === "nodes") this._loadNodes();
    if (tab === "stats") this._loadStats();
  }

  async _sendMessage() {
    if (!this._messageInput.trim()) return;

    const data = { text: this._messageInput };
    const conv = this._selectedConversation;

    if (this._dms.includes(conv)) {
      data.to = conv;
    } else if (conv) {
      data.channel = conv;
    }

    const result = await this._wsCommand("meshtastic_ui/send_message", data);
    if (result && result.success) {
      this._messageInput = "";
    }
  }

  _onInputKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      this._sendMessage();
    }
  }

  _sortNodes(column) {
    if (this._sortColumn === column) {
      this._sortAsc = !this._sortAsc;
    } else {
      this._sortColumn = column;
      this._sortAsc = true;
    }
  }

  _getSortedNodes() {
    const entries = Object.entries(this._nodes);
    const col = this._sortColumn;
    const asc = this._sortAsc;

    return entries.sort(([, a], [, b]) => {
      let va = a[col] ?? "";
      let vb = b[col] ?? "";

      if (col === "battery" || col === "snr" || col === "hops") {
        va = parseFloat(va) || 0;
        vb = parseFloat(vb) || 0;
      } else {
        va = String(va).toLowerCase();
        vb = String(vb).toLowerCase();
      }

      if (va < vb) return asc ? -1 : 1;
      if (va > vb) return asc ? 1 : -1;
      return 0;
    });
  }

  _formatTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  }

  _formatLastSeen(iso) {
    if (!iso) return "Unknown";
    try {
      const d = new Date(iso);
      const now = new Date();
      const diff = Math.floor((now - d) / 1000);
      if (diff < 60) return "Just now";
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return `${Math.floor(diff / 86400)}d ago`;
    } catch {
      return "Unknown";
    }
  }

  static get styles() {
    return css`
      :host {
        display: block;
        height: 100%;
        background: var(--primary-background-color);
        color: var(--primary-text-color);
      }

      .tabs {
        display: flex;
        border-bottom: 1px solid var(--divider-color);
        background: var(--card-background-color);
        padding: 0 16px;
      }

      .tab {
        padding: 12px 20px;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
        transition: all 0.2s;
        user-select: none;
      }

      .tab:hover {
        color: var(--primary-text-color);
      }

      .tab.active {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }

      .content {
        padding: 16px;
        height: calc(100% - 49px);
        overflow-y: auto;
        box-sizing: border-box;
      }

      /* Radio tab */
      .iframe-container {
        width: 100%;
        height: calc(100vh - 150px);
        border: none;
        border-radius: 8px;
        overflow: hidden;
      }

      .iframe-container iframe {
        width: 100%;
        height: 100%;
        border: none;
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 16px;
        color: var(--secondary-text-color);
      }

      .empty-state ha-icon {
        --mdc-icon-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }

      /* Messages tab */
      .messages-layout {
        display: flex;
        gap: 16px;
        height: calc(100vh - 150px);
      }

      .conversation-list {
        width: 240px;
        flex-shrink: 0;
        overflow-y: auto;
        border-right: 1px solid var(--divider-color);
        padding-right: 16px;
      }

      .conversation-item {
        padding: 10px 12px;
        cursor: pointer;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: background 0.15s;
      }

      .conversation-item:hover {
        background: var(--secondary-background-color);
      }

      .conversation-item.active {
        background: var(--primary-color);
        color: var(--text-primary-color);
      }

      .conversation-header {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        padding: 8px 12px 4px;
        letter-spacing: 0.5px;
      }

      .chat-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
      }

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 8px 0;
      }

      .chat-bubble {
        max-width: 75%;
        padding: 8px 14px;
        margin: 4px 0;
        border-radius: 16px;
        font-size: 14px;
        line-height: 1.4;
        word-break: break-word;
      }

      .chat-bubble.incoming {
        background: var(--secondary-background-color);
        border-bottom-left-radius: 4px;
        align-self: flex-start;
      }

      .chat-bubble .sender {
        font-size: 11px;
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 2px;
      }

      .chat-bubble .time {
        font-size: 10px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }

      .chat-input-row {
        display: flex;
        gap: 8px;
        padding-top: 12px;
        border-top: 1px solid var(--divider-color);
      }

      .chat-input-row input {
        flex: 1;
        padding: 10px 14px;
        border: 1px solid var(--divider-color);
        border-radius: 20px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
        outline: none;
      }

      .chat-input-row input:focus {
        border-color: var(--primary-color);
      }

      .send-btn {
        padding: 8px 20px;
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
      }

      .send-btn:hover {
        opacity: 0.9;
      }

      /* Nodes table */
      .nodes-table {
        width: 100%;
        border-collapse: collapse;
      }

      .nodes-table th {
        text-align: left;
        padding: 10px 12px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        border-bottom: 2px solid var(--divider-color);
        cursor: pointer;
        user-select: none;
        letter-spacing: 0.5px;
      }

      .nodes-table th:hover {
        color: var(--primary-text-color);
      }

      .sort-indicator {
        margin-left: 4px;
        font-size: 10px;
      }

      .nodes-table td {
        padding: 10px 12px;
        border-bottom: 1px solid var(--divider-color);
        font-size: 14px;
      }

      .nodes-table tr:hover td {
        background: var(--secondary-background-color);
      }

      /* Stats cards */
      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 16px;
      }

      .stat-card {
        background: var(--card-background-color);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid var(--divider-color);
      }

      .stat-card .label {
        font-size: 13px;
        color: var(--secondary-text-color);
        font-weight: 500;
        margin-bottom: 8px;
      }

      .stat-card .value {
        font-size: 32px;
        font-weight: 700;
        color: var(--primary-text-color);
      }

      ha-card {
        margin-bottom: 16px;
      }
    `;
  }

  render() {
    return html`
      <div class="tabs">
        ${TABS.map(
          (tab) => html`
            <div
              class="tab ${this._activeTab === tab ? "active" : ""}"
              @click=${() => this._setTab(tab)}
            >
              ${TAB_LABELS[tab]}
            </div>
          `
        )}
      </div>
      <div class="content">${this._renderTab()}</div>
    `;
  }

  _renderTab() {
    switch (this._activeTab) {
      case "radio":
        return this._renderRadioTab();
      case "messages":
        return this._renderMessagesTab();
      case "nodes":
        return this._renderNodesTab();
      case "stats":
        return this._renderStatsTab();
      default:
        return html``;
    }
  }

  _renderRadioTab() {
    if (!this._gateways.length) {
      return html`
        <div class="empty-state">
          <ha-icon icon="mdi:radio-handheld"></ha-icon>
          <div>No Meshtastic gateways found</div>
          <div style="font-size: 13px; margin-top: 8px;">
            Make sure the Meshtastic integration is configured.
          </div>
        </div>
      `;
    }

    return html`
      ${this._gateways.map(
        (gw) => html`
          <ha-card>
            <div style="padding: 16px;">
              <div style="font-weight: 500; margin-bottom: 8px;">${gw.name}</div>
              <div class="iframe-container">
                <iframe
                  src="${gw.web_url}"
                  title="${gw.name} Web Client"
                  allow="serial"
                ></iframe>
              </div>
            </div>
          </ha-card>
        `
      )}
    `;
  }

  _renderMessagesTab() {
    const allConversations = [...this._channels, ...this._dms];

    if (!allConversations.length) {
      return html`
        <div class="empty-state">
          <ha-icon icon="mdi:message-text-outline"></ha-icon>
          <div>No messages yet</div>
          <div style="font-size: 13px; margin-top: 8px;">
            Messages will appear here as they arrive from the mesh network.
          </div>
        </div>
      `;
    }

    const selected = this._selectedConversation || allConversations[0] || "";
    const currentMessages = this._messages[selected] || [];

    return html`
      <div class="messages-layout">
        <div class="conversation-list">
          ${this._channels.length
            ? html`
                <div class="conversation-header">Channels</div>
                ${this._channels.map(
                  (ch) => html`
                    <div
                      class="conversation-item ${selected === ch ? "active" : ""}"
                      @click=${() => (this._selectedConversation = ch)}
                    >
                      ${ch}
                    </div>
                  `
                )}
              `
            : ""}
          ${this._dms.length
            ? html`
                <div class="conversation-header">Direct Messages</div>
                ${this._dms.map(
                  (dm) => html`
                    <div
                      class="conversation-item ${selected === dm ? "active" : ""}"
                      @click=${() => (this._selectedConversation = dm)}
                    >
                      ${dm}
                    </div>
                  `
                )}
              `
            : ""}
        </div>

        <div class="chat-area">
          <div class="chat-messages">
            ${currentMessages.map(
              (msg) => html`
                <div class="chat-bubble incoming">
                  <div class="sender">${msg.from || "Unknown"}</div>
                  <div>${msg.text}</div>
                  <div class="time">${this._formatTime(msg.timestamp)}</div>
                </div>
              `
            )}
            ${!currentMessages.length
              ? html`
                  <div class="empty-state">
                    <div>No messages in this conversation</div>
                  </div>
                `
              : ""}
          </div>

          <div class="chat-input-row">
            <input
              type="text"
              placeholder="Type a message..."
              .value=${this._messageInput}
              @input=${(e) => (this._messageInput = e.target.value)}
              @keydown=${this._onInputKeydown}
            />
            <button class="send-btn" @click=${this._sendMessage}>Send</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderNodesTab() {
    const sortedNodes = this._getSortedNodes();

    if (!sortedNodes.length) {
      return html`
        <div class="empty-state">
          <ha-icon icon="mdi:access-point-network-off"></ha-icon>
          <div>No mesh nodes discovered yet</div>
          <div style="font-size: 13px; margin-top: 8px;">
            Nodes will appear as they communicate on the mesh.
          </div>
        </div>
      `;
    }

    const columns = [
      { key: "name", label: "Name" },
      { key: "snr", label: "SNR" },
      { key: "hops", label: "Hops" },
      { key: "battery", label: "Battery" },
      { key: "_last_seen", label: "Last Seen" },
    ];

    return html`
      <ha-card>
        <table class="nodes-table">
          <thead>
            <tr>
              ${columns.map(
                (col) => html`
                  <th @click=${() => this._sortNodes(col.key)}>
                    ${col.label}
                    ${this._sortColumn === col.key
                      ? html`<span class="sort-indicator"
                          >${this._sortAsc ? "▲" : "▼"}</span
                        >`
                      : ""}
                  </th>
                `
              )}
            </tr>
          </thead>
          <tbody>
            ${sortedNodes.map(
              ([nodeId, node]) => html`
                <tr>
                  <td>${node.name || nodeId}</td>
                  <td>${node.snr ?? "—"}</td>
                  <td>${node.hops ?? "—"}</td>
                  <td>
                    ${node.battery != null ? `${node.battery}%` : "—"}
                  </td>
                  <td>${this._formatLastSeen(node._last_seen)}</td>
                </tr>
              `
            )}
          </tbody>
        </table>
      </ha-card>
    `;
  }

  _renderStatsTab() {
    const cards = [
      {
        label: "Messages Today",
        value: this._stats.messages_today,
        icon: "mdi:message-text",
      },
      {
        label: "Active Nodes",
        value: this._stats.active_nodes,
        icon: "mdi:access-point",
      },
      {
        label: "Total Nodes",
        value: this._stats.total_nodes,
        icon: "mdi:radio-tower",
      },
      {
        label: "Channels",
        value: this._stats.channel_count,
        icon: "mdi:forum",
      },
    ];

    return html`
      <div class="stats-grid">
        ${cards.map(
          (card) => html`
            <div class="stat-card">
              <div class="label">
                <ha-icon icon="${card.icon}" style="--mdc-icon-size: 18px; vertical-align: middle; margin-right: 4px;"></ha-icon>
                ${card.label}
              </div>
              <div class="value">${card.value}</div>
            </div>
          `
        )}
      </div>
    `;
  }
}

customElements.define("meshtastic-ui-panel", MeshtasticUiPanel);
