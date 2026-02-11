document.addEventListener("DOMContentLoaded", function() {
  const messages = JSON.parse(document.getElementById('django-messages').textContent);
  if (messages.length > 0) {
    messages.forEach(function(message) {
      var toastHTML = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
          <div class="toast-header">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
          <div class="toast-body">
            ${message.message}
          </div>
        </div>`;
      var toastContainer = document.getElementById('toast-container');
      toastContainer.innerHTML += toastHTML;
    });
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function(toastEl) {
      return new bootstrap.Toast(toastEl, {autohide: true}).show();
    });
  }
});
