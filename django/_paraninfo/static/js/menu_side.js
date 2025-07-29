

document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');
    const menuOptions = document.querySelector('.menu-options_side');

    // Restaurar o estado do menu a partir do localStorage
    const isExpanded = localStorage.getItem('menuExpanded') === 'true';
    if (isExpanded) {
        sidebar.classList.add('expanded');
        menuOptions.style.display = 'block'; // Mostrar opções
        toggleBtn.innerHTML = '<img src="/static/media/icons/menu_left.svg" alt="Recolher" >';
    } else {
        sidebar.classList.remove('expanded');
        menuOptions.style.display = 'none'; // Ocultar opções
        toggleBtn.innerHTML = '<img src="/static/media/icons/menu_right.svg" alt="Expandir"  >';
    }

    // Adicionar evento de clique ao botão de alternância
    toggleBtn.addEventListener('click', function () {
        if (sidebar.classList.contains('expanded')) {
            // Ocultar texto antes de iniciar a animação de fechamento
            menuOptions.style.display = 'none';
            sidebar.classList.remove('expanded');
            toggleBtn.innerHTML = '<img src="/static/media/icons/menu_right.svg" alt="Expandir" class="toggle-btn";">';
            localStorage.setItem('menuExpanded', 'false'); // Salvar estado no localStorage
        } else {
            sidebar.classList.add('expanded');
            // Exibir texto após concluir a animação de expansão
            setTimeout(() => {
                menuOptions.style.display = 'block';
            }, 300); // Tempo da animação (deve coincidir com o CSS)
            toggleBtn.innerHTML = '<img src="/static/media/icons/menu_left.svg" alt="Recolher" class="toggle-btn";">';
            localStorage.setItem('menuExpanded', 'true'); // Salvar estado no localStorage
        }
    });
});

// Função para chamar carregar uma página
function openAnalisePage() {
    // Mostra imagem da ampulheta
    showLoadingOverlay();

    // Carrega a página balance/analise-movimentacao
    window.location.href = '/transaction/analise-movimentacao';
}