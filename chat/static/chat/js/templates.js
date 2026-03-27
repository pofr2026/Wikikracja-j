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

  <div class='messages'>
    <div class='empty-chat-message'>
      ${_("This room is empty, be the first one to write something.")}
    </div>
  </div>

  <div style='position: relative'>
    <div class='image-preview-container' style='display:none'>
      <div class='preview-images'></div>
      <div class='delete-images-preview'>
        <i class='fas fa fa-times'></i>
      </div>
    </div>
  </div> 

  <div class='chat-controls sticky-bottom'>
    <div class='checkbox-container'>
      <% if (is_public) { %>
        <input class='anonymous-switch' id='anonymous-switch-id' type='checkbox' />
        <label for='anonymous-switch-id'>${_("Anonymous")}</label>
      <% } %>
    </div>

    <div>
        <!-- Those two have to go one after another for some CSS trickery -->
          <input type='file' id='file-input' class='file-input' multiple='multiple'/>
          <label class='btn btn-primary chat-control' for='file-input'>
              <i class='fas fa-image'></i>
          </label>
        <!-- Those two-->

      <div class='chat-controls-row'>
        <input id='message-input'>
        <button class='send-message chat-control btn btn-primary'>
          <i class='fas fa-paper-plane'></i>
        </button>
      </div>
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

    <div class='message-header'>
      <span class='username'><%=username%></span>
      <div class='message-info'>
        <div class='show-history' <% if (!edited) { %> style='display:none' <% } %>
          data-message-id='<%-message_id%>'> ${_("edited")}
        </div>
        <% if (own) { %>
          <div class='edit-message ms-1' data-message-id="<%-message_id%>" >${_("edit")}</div>
        <% } %>
        <div class='message-timestamp ms-1' data-message-id='<%-message_id%>'><%- latest_ts %></div>
        <button type='button'
          class='btn btn-link btn-sm p-0 ms-1 copy-link-btn copy-message-url'
          data-room-id='<%-room_id%>'
          data-message-id='<%-message_id%>'
          title='${_("Copy link")}'
          aria-label='${_("Copy message link")}'>
          <i class='fas fa-link'></i>
        </button>
      </div>
    </div>

    <div class='msg-body'>
      <div class='attachment-image-container'>
        <% if (attachments && attachments.images) { %>
          <% for (let filename of attachments.images) { %>
            <img class='attached-image' src='/media/uploads/<%-filename %>'>
          <% } %>
        <% } %>
      </div>
      <span class='msg-text'><%-message%></span>
    </div>

    <div class='footer'>
      <% if (type == "public") { %>
        <div class='d-flex d-flex justify-content-end'>
          <div data-event-name='upvote' data-message-id="<%-message_id%>" class='msg-vote'>
            <i class='fas fa-check'></i>
          <div class='msg-upvotes'><%-upvotes%></div>
          </div>
          <div data-event-name='downvote' data-message-id="<%-message_id%>" class='msg-vote'>
            <i class='fas fa-times'></i>
          <div class='msg-downvotes'><%-downvotes%></div>
          </div>
        </div>
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