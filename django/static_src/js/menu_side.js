
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');
    const menuOptions = document.getElementById('menu-options-side');
    if (!sidebar || !toggleBtn || !menuOptions) return;

    const savedState = localStorage.getItem('menuExpanded');
    const setExpanded = (isExpanded) => {
        sidebar.classList.toggle('expanded', isExpanded);
        toggleBtn.setAttribute('aria-expanded', String(isExpanded));
        toggleBtn.setAttribute('aria-label', isExpanded ? 'Recolher menu' : 'Expandir menu');
        toggleBtn.querySelector('img').src = isExpanded ? '/static/menu_left.svg' : '/static/menu_right.svg';
        localStorage.setItem('menuExpanded', String(isExpanded));
    };

    // Preserva o menu aberto na primeira visita e restaura escolhas anteriores.
    setExpanded(savedState === null || savedState === 'true');

    toggleBtn.addEventListener('click', function () {
        setExpanded(!sidebar.classList.contains('expanded'));
    });
});

// Função para chamar carregar uma página
function openAnalisePage() {
    // Mostra imagem da ampulheta
    showLoadingOverlay();

    // Carrega a página balance/analise-movimentacao
    window.location.href = '/transaction/analise-movimentacao';
}