// Ana JavaScript Dosyası

// Sayfa yüklendiğinde çalışacak fonksiyonlar
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltip'leri etkinleştir
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Flash mesajları için otomatik kapanma
    var flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(alert) {
        setTimeout(function() {
            var closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000); // 5 saniye sonra kapat
    });
    
    // Görsel önizleme için tıklama olayı
    var imagePreviewLinks = document.querySelectorAll('.image-preview-link');
    imagePreviewLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var imageUrl = this.getAttribute('data-image-url');
            var title = this.getAttribute('data-title') || 'Görsel Önizleme';
            
            // Modal oluştur
            var modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'imagePreviewModal';
            modal.setAttribute('tabindex', '-1');
            modal.setAttribute('aria-labelledby', 'imagePreviewModalLabel');
            modal.setAttribute('aria-hidden', 'true');
            
            modal.innerHTML = `
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="imagePreviewModalLabel">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${imageUrl}" class="img-fluid rounded" alt="${title}">
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            var modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
            
            // Modal kapatıldığında DOM'dan kaldır
            modal.addEventListener('hidden.bs.modal', function() {
                document.body.removeChild(modal);
            });
        });
    });
    
    // Form gönderimlerinde yükleme göstergesi
    var forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            var submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                var originalText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> İşleniyor...';
                
                // Form gönderildikten sonra butonu eski haline getir
                setTimeout(function() {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }, 3000); // 3 saniye sonra
            }
        });
    });
    
    // Şifre göster/gizle düğmeleri
    var passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            var passwordInput = document.getElementById(this.getAttribute('data-target'));
            if (passwordInput) {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                } else {
                    passwordInput.type = 'password';
                    this.innerHTML = '<i class="fas fa-eye"></i>';
                }
            }
        });
    });
    
    // Tablo satırlarına tıklama olayı
    var tableRows = document.querySelectorAll('.clickable-row');
    tableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            window.location.href = this.getAttribute('data-href');
        });
    });
});

// Sayfa yenileme fonksiyonu
function refreshPage() {
    location.reload();
}

// Belirli bir süre sonra sayfayı yenileme
function autoRefresh(minutes) {
    setTimeout(function() {
        refreshPage();
    }, minutes * 60 * 1000);
}

// API'den veri çekme fonksiyonu
function fetchData(url, callback) {
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            callback(null, data);
        })
        .catch(error => {
            console.error('Fetch error:', error);
            callback(error, null);
        });
}

// Tarih formatı fonksiyonu
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('tr-TR', options);
}

// Metin kısaltma fonksiyonu
function truncateText(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }
    return text.substr(0, maxLength) + '...';
}

// Hata mesajı gösterme fonksiyonu
function showError(message) {
    var alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Kapat"></button>
    `;
    
    var container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5 saniye sonra otomatik kapat
    setTimeout(function() {
        var closeButton = alertDiv.querySelector('.btn-close');
        if (closeButton) {
            closeButton.click();
        }
    }, 5000);
}

// Başarı mesajı gösterme fonksiyonu
function showSuccess(message) {
    var alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Kapat"></button>
    `;
    
    var container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5 saniye sonra otomatik kapat
    setTimeout(function() {
        var closeButton = alertDiv.querySelector('.btn-close');
        if (closeButton) {
            closeButton.click();
        }
    }, 5000);
} 