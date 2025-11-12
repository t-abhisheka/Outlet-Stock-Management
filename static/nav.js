document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const sideNav = document.getElementById('side-nav');
    const overlay = document.getElementById('overlay');

    function openNav() {
        sideNav.classList.add('active');
        overlay.classList.add('active');
    }

    function closeNav() {
        sideNav.classList.remove('active');
        overlay.classList.remove('active');
    }

    menuBtn.addEventListener('click', openNav);
    closeBtn.addEventListener('click', closeNav);
    overlay.addEventListener('click', closeNav);
});