// Seleciona os elementos do menu e do botão
const menu = document.querySelector('.menu-options');
const menuButton = document.querySelector('.menu-button');

// Variável para rastrear se o mouse está sobre o menu ou o botão
let isMouseOverMenuOrButton = false;

// Alterna o menu ao clicar no botão
menuButton.addEventListener('click', () => {
    if (menu.classList.contains('active')) {
        // Fecha o menu
        closeMenu();
    } else {
        // Abre o menu
        openMenu();
    }
});

// Abre o menu
function openMenu() {
    menu.style.display = 'block'; // Torna o menu visível
    setTimeout(() => {
        menu.style.opacity = '1'; // Torna o menu opaco
    }, 10); // Pequeno atraso para ativar a transição
    menu.classList.add('active');
    menuButton.classList.add('active'); // Adiciona a classe 'active' ao botão
}

// Fecha o menu
function closeMenu() {
    menu.classList.remove('active');
    menuButton.classList.remove('active'); // Remove a classe 'active' do botão
    menu.style.opacity = '0'; // Torna o menu transparente
    setTimeout(() => {
        menu.style.display = 'none'; // Esconde o menu após a transição
    }, 500); // Tempo deve coincidir com a transição no CSS
}

// Mantém o menu aberto enquanto o mouse estiver sobre o menu ou o botão
menu.addEventListener('mouseenter', () => {
    isMouseOverMenuOrButton = true;
});

menu.addEventListener('mouseleave', () => {
    isMouseOverMenuOrButton = false;
    setTimeout(() => {
        if (!isMouseOverMenuOrButton) {
            closeMenu();
        }
    }, 300); // Timeout para evitar fechamento imediato
});

menuButton.addEventListener('mouseenter', () => {
    isMouseOverMenuOrButton = true;
});

menuButton.addEventListener('mouseleave', () => {
    isMouseOverMenuOrButton = false;
    setTimeout(() => {
        if (!isMouseOverMenuOrButton) {
            closeMenu();
        }
    }, 300); // Timeout para evitar fechamento imediato
});