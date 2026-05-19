// ============================================
// AIRA App Init — har bir sahifa boshida ishlaydi
// IndexedDB tayyor bo'lguncha kutadi, keyin sahifa render qiladi
// ============================================

(async function() {
  // Loading ekran ko'rsatish
  const loader = document.createElement('div');
  loader.id = 'aira-loader';
  loader.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, #EAF3FB 0%, #EDEBFA 100%);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 99999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;
  loader.innerHTML = `
    <div style="
      width: 60px; height: 60px;
      background: linear-gradient(135deg, #185FA5, #042C53);
      border-radius: 16px;
      display: flex; align-items: center; justify-content: center;
      color: white; font-weight: 700; font-size: 14px;
      letter-spacing: 0.5px;
      margin-bottom: 16px;
      box-shadow: 0 10px 30px rgba(4, 44, 83, 0.2);
      animation: airaPulse 1.5s ease-in-out infinite;
    ">AIRA</div>
    <div style="font-size: 13px; color: #4A5568; font-weight: 500;">Yuklanmoqda...</div>
    <style>
      @keyframes airaPulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
      }
    </style>
  `;
  document.body.appendChild(loader);

  // Storage init kutilsin
  try {
    await Storage.init();
    console.log('✓ Storage tayyor');
  } catch (e) {
    console.error('Storage init xatosi:', e);
  }

  // Loader olib tashlash
  loader.style.transition = 'opacity 0.3s';
  loader.style.opacity = '0';
  setTimeout(() => loader.remove(), 300);

  // Sahifa init funksiyasi (har bir sahifada e'lon qilingan)
  if (typeof window.initPage === 'function') {
    try {
      window.initPage();
    } catch (e) {
      console.error('Page init xatosi:', e);
    }
  }
})();
