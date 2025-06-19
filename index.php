<?php
// Database connection settings
$host = "localhost";
$username = "admin";
$password = "15F4FSSF4Ssa#fasd5UI5%";
$database = "dbParaninfo";

// Connect to the database
$conn = new mysqli($host, $username, $password, $database);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Initialize variables
$result = null;
$user = null;
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Get the input values
    $codigo_pagamento = intval($_POST["codigo_pagamento"]);
    $codigo_aluno = intval($_POST["codigo_aluno"]);
    $codigo_associado = $codigo_aluno * 100 + $codigo_pagamento;

    // Query the database
    $sql = "SELECT * FROM `tbLivroCaixa` WHERE `codigo_pagamento` = $codigo_pagamento;";
    $sql1 = "SELECT * FROM `tbAssociados` WHERE `codigo_associado` = $codigo_associado;";
    $result = $conn->query($sql);
    $user = $conn->query($sql1);
    
   // Check if a result was found
    if ($user && $user->num_rows > 0) {
        $user_row = $user->fetch_assoc();
        $user_name = $user_row["nome_de_guerra"];
    } else {
        $user_name = "Aluno não encontrado";
    }

}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Menu</title>
</head>
<body>
    <h1>Comissão de formatura - CMBH</h1>
    <h2>Extrato de pagamento para simples conferência</h2>
    <form method="POST">
        <label for="codigo_pagamento">Entre com o código de pagamento:</label>
        <input type="text" id="codigo_pagamento" name="codigo_pagamento" required><br><br>

        <label for="codigo_aluno">Entre com o código do aluno:</label>
        <input type="text" id="codigo_aluno" name="codigo_aluno" required><br><br>

        <button type="submit">Enviar</button>
    </form>

    <?php if ($result && $result->num_rows > 0 && $user->num_rows > 0): ?>

        <h2>Extrato de pagamentos para o associado: <?php echo htmlspecialchars($user_name);  ?></h2>
        <p>Código de associado: <?php echo $codigo_associado; ?></p>
        <table border="1">
            <tr>
                <th>Id</th>
                <th>Associado</th>
                <th>Data</th>
                <th>Valor pago</th>
                <th>Total créditos</th>
                <th>Total em aberto</th>
                <th>Total mensalidades pagas</th>
            </tr>
            <?php while ($row = $result->fetch_assoc()): ?>
                <tr>
                    <td><?php echo htmlspecialchars($row["id"]); ?></td>
                    <td><?php echo htmlspecialchars($row["codigo_pagamento"]); ?></td>
                    <td><?php echo htmlspecialchars($row["data_pagamento"]); ?></td>
                    <td><?php echo htmlspecialchars($row["valor_pago"]); ?></td>
                    <td><?php echo htmlspecialchars($row["total_creditos"]); ?></td>
                    <td><?php echo htmlspecialchars($row["total_em_aberto"]); ?></td>
                    <td><?php echo htmlspecialchars($row["total_pago"]); ?></td>
                </tr>
            <?php endwhile; ?>
        </table>
    <?php elseif ($codigo_aluno > 0):?>
        <p>Código de associado inválido.</p>
    <?php elseif ($_SERVER["REQUEST_METHOD"] == "POST"): ?>
        <p>Nenhum resultado encontrado.</p>
    <?php endif; ?>
    <p>(*) apenas para demonstração. Não é valido como comprovação de pagamento.</p>
    <?php $conn->close(); ?>
</body>
</html>