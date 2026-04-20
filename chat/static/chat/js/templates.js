/**
 * @file
 * EJS template definitions for chat UI components.
 * Contains template literals for room layout, message display, and history modal.
 * Templates are compiled using EJS (Embedded JavaScript Templates).
 */

import { _ } from './utility.js';

/**
 * Room template - main chat room layout
 * Contains message container, image preview, and input controls
 * @type {string}
 */
const room_template = `
<div id='room'>

  <div class="chat-breadcrumb" id="chat-breadcrumb" aria-label="Lokalizacja"></div>

  <div class='messages'>
    <div class='empty-chat-message'>
      ${_("This room is empty, be the first one to write something.")}
    </div>
  </div>

  <div class='image-preview-container' style='display:none'>
    <div class='preview-images'></div>
    <div class='delete-images-preview'>
      <i class='fas fa fa-times'></i>
    </div>
  </div>

  <div class='chat-controls'>
    <div class="reply-preview" id="reply-preview" style="display:none">
      <span class="reply-preview-label">↩ </span>
      <span class="reply-preview-text" id="reply-preview-text"></span>
      <button class="reply-preview-close" id="reply-preview-close" type="button" title="Anuluj odpowiedź">✕</button>
    </div>
    <div class='chat-controls-row'>
      <!-- Image upload button -->
      <input type='file' id='file-input' class='file-input' multiple='multiple'/>
      <label class='btn btn-primary chat-control' for='file-input'>
        <i class='fas fa-image'></i>
      </label>
      
      <!-- Anonymous toggle button (icon only) -->
      <% if (is_public) { %>
        <button class='btn chat-control anonymous-toggle' id='anonymous-toggle' type='button' title='${_("Anonymous")}'>
          <i class='fas fa-user-secret'></i>
        </button>
      <% } %>
      
      <!-- Rich text input -->
      <div id="message-input" class="message-input-rich" contenteditable="true"
           role="textbox" aria-multiline="true" aria-label="${_("Divide the message into several parts...")}"
           data-placeholder="${_("Divide the message into several parts...")}"></div>

      <!-- Send button -->
      <button class='send-message chat-control btn btn-primary'>
        <i class='fas fa-paper-plane'></i>
      </button>
    </div>
    <div class="fmt-toolbar" id="fmt-toolbar">
      <button class="fmt-btn" data-cmd="bold"      title="Ctrl+B"><b>B</b></button>
      <button class="fmt-btn" data-cmd="italic"    title="Ctrl+I"><i>I</i></button>
      <button class="fmt-btn" data-cmd="underline" title="Ctrl+U"><u>U</u></button>
    </div>
    <div class="msg-counter" id="msg-counter">
      <span id="msg-counter-val"><%- messageMaxLength %></span> / <%- messageMaxLength %>
    </div>
  </div>
</div>
`;

/**
 * Message template - individual message display
 * Shows username, timestamp, content, attachments, and voting controls
 * @type {string}
 */
const message_template = `
<div class='message <% if (own) { %> own <% } %>' data-message-id="<%-message_id%>" data-room-id="<%-room_id%>">
  <div class='message-content'>

    <div class='msg-body'>
      <% if (reply_to) { %>
      <div class="msg-quote" data-reply-id="<%-reply_to.id%>" data-target-id="<%-reply_to.id%>" role="button" title="Przejdź do oryginału">
        <span class="msg-quote-mark">"</span>
        <span class="msg-quote-author">@<%-reply_to.username%>:</span>
        <span class="msg-quote-text"><%-reply_to.text_snippet%></span>
        <span class="msg-quote-mark">"</span>
        <button class="msg-quote-jump" data-target-id="<%-reply_to.id%>" type="button" title="Przejdź do oryginału">↗</button>
      </div>
      <% } %>
      <div class='attachment-image-container'>
        <% if (attachments && attachments.images) { %>
          <% for (let filename of attachments.images) { %>
            <img class='attached-image' src='/media/uploads/<%-filename %>'>
          <% } %>
        <% } %>
      </div>
      <span class='msg-text'><%-message%></span>
    </div>

    <div class='message-header'>
      <div class='message-header-left'>
        <span class='username'><%=username%></span>
        <span class='message-timestamp ms-2' data-message-id='<%-message_id%>'><%- latest_ts %></span>
        <button type='button' class='btn btn-sm ms-1 message-btn show-history' <% if (!edited) { %> style='display:none' <% } %>
          data-message-id='<%-message_id%>'
          title='${_("edited")}'>
          <i class='fas fa-history'></i>
        </button>
        <% if (own) { %>
          <button type='button' class='btn btn-sm ms-1 message-btn edit-message' data-message-id="<%-message_id%>"
            title='${_("edit")}'>
            <i class='fas fa-edit'></i>
          </button>
        <% } %>
        <button type='button'
          class='btn btn-sm ms-1 message-btn reply-btn'
          data-message-id='<%-message_id%>'
          data-username='<%=username%>'
          data-snippet='<%-message.replace(/<[^>]*>/g,"").slice(0,80)%>'
          title='Odpowiedz'>
          <i class='fas fa-reply'></i>
        </button>
        <button type='button'
          class='btn btn-sm ms-1 message-btn copy-message-url'
          data-room-id='<%-room_id%>'
          data-message-id='<%-message_id%>'
          title='${_("Copy link")}'>
          <i class='fas fa-link'></i>
        </button>
      </div>
      <div class='message-header-right'></div>
    </div>

    <%
      const _totalVotes = upvotes + downvotes;
      const _pct = _totalVotes > 0 ? Math.round((upvotes / _totalVotes) * 100) : 0;
      const _barCls = _pct >= 60 ? 'vote-bar--positive' : (_pct >= 40 ? 'vote-bar--neutral' : 'vote-bar--negative');
    %>
    <div class="msg-meta-row">
      <% if (type == "public") { %>
        <button type='button' data-event-name='upvote' data-message-id="<%-message_id%>" class='btn btn-sm message-btn msg-vote' title='${_("Upvote")}'>
          <i class='fas fa-thumbs-up'></i>
          <span class='msg-upvotes'><%-upvotes%></span>
        </button>
        <button type='button' data-event-name='downvote' data-message-id="<%-message_id%>" class='btn btn-sm message-btn msg-vote' title='${_("Downvote")}'>
          <i class='fas fa-thumbs-down'></i>
          <span class='msg-downvotes'><%-downvotes%></span>
        </button>
      <% } %>

      <% if (_totalVotes >= 3) { %>
        <div class="vote-bar-wrap">
          <div class="vote-bar-fill <%- _barCls %>" style="width:<%- _pct %>%"></div>
        </div>
        <span class="vote-bar-label"><%- _pct %>% popiera</span>
      <% } %>

      <span class="msg-divider" aria-hidden="true"></span>

      <% for (const [_key, _emoji, _label] of [['bulb','💡','Ciekawe'],['question','❓','Mam pytanie']]) { %>
        <button class="reaction-btn<% if ((your_reactions||[]).includes(_key)) { %> reaction-btn--active<% } %>"
                data-reaction="<%- _key %>" data-message-id="<%- message_id %>"
                type="button" title="<%- _label %>">
          <%- _emoji %><% if ((reactions[_key]||0) > 0) { %><span class="reaction-count"><%- reactions[_key] %></span><% } %>
        </button>
      <% } %>

      <% if (read_by && read_by.length) { %>
        <% const _vis = read_by.slice(0,3); const _extra = read_by.length - _vis.length; %>
        <div class="msg-read-by">
          <% for (const _u of _vis) { %><img class="msg-avatar" src="<%- _u.avatar_url %>" title="<%- _u.username %>" alt="<%- _u.username %>"><% } %>
          <% if (_extra > 0) { %><span class="msg-read-extra">+<%- _extra %></span><% } %>
        </div>
      <% } else { %>
        <div class="msg-read-by"></div>
      <% } %>
    </div>

  </div>
</div>
`;

/**
 * Message history template - table showing edit history
 * Displays timestamped table of message edits
 * @type {string}
 */
const history_template = `
<table class='table' style='border-bottom: 1px solid #dee2e6;'>
<% for (let [i, entry] of Object.entries(history)) { %>
  <tr>
    <td style='width: 0'><%- parseInt(i) + 1 %>.</td>
    <td> <%- entry.text %> </td>
    <td style='text-align: end; font-size: smaller; color: gray;'>
      <%- entry.formattedTime %>
    </td>
  </tr>
<% } %>
</table>
`;

/**
 * Compiles room template into a render function
 * @returns {Function} - EJS template function
 */
export const Room = ejs.compile(room_template);

/**
 * Compiles message template into a render function
 * @returns {Function} - EJS template function
 */
export const Message = ejs.compile(message_template);

/**
 * Compiles history template into a render function
 * @returns {Function} - EJS template function
 */
export const MessageHistory = ejs.compile(history_template);