// Seleciona os elementos do menu do usuário e do botão
const menuUser = document.querySelector('.menu-user-options');
const menuUserButton = document.querySelector('.menu-user-button');

// Alterna o menu ao clicar no botão
menuUserButton.addEventListener('click', () => {
    if (menuUser.classList.contains('active')) {
        closeUserMenu();
    } else {
        openUserMenu();
    }
});

// Abre o menu do usuário
function openUserMenu() {
    menuUser.style.display = 'block'; // Torna o menu visível
    setTimeout(() => {
        menuUser.style.opacity = '1'; // Torna o menu opaco
    }, 10); // Pequeno atraso para ativar a transição
    menuUser.classList.add('active');
    menuUserButton.classList.add('active'); // Adiciona a classe 'active' ao botão
}

// Fecha o menu do usuário
function closeUserMenu() {
    menuUser.classList.remove('active');
    menuUserButton.classList.remove('active'); // Remove a classe 'active' do botão
    menuUser.style.opacity = '0'; // Torna o menu transparente
    setTimeout(() => {
        menuUser.style.display = 'none'; // Esconde o menu após a transição
    }, 500); // Tempo deve coincidir com a transição no CSS
}

// Mantém o menu aberto enquanto o mouse estiver sobre o menu ou o botão
menuUser.addEventListener('mouseenter', () => {
    isMouseOverMenuOrButton = true;
});

menuUser.addEventListener('mouseleave', () => {
    isMouseOverMenuOrButton = false;
    setTimeout(() => {
        if (!isMouseOverMenuOrButton) {
            closeUserMenu();
        }
    }, 300); // Timeout para evitar fechamento imediato
});

menuUserButton.addEventListener('mouseenter', () => {
    isMouseOverMenuOrButton = true;
});

menuUserButton.addEventListener('mouseleave', () => {
    isMouseOverMenuOrButton = false;
    setTimeout(() => {
        if (!isMouseOverMenuOrButton) {
            closeUserMenu();
        }
    }, 300); // Timeout para evitar fechamento imediato
});