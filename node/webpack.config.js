const path = require('path');

module.exports = {
    mode: 'development', // Define o modo como 'development'
    entry: './src/index.js', // Arquivo de entrada
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'bundle.js', // Arquivo de saída
    },
    module: {
        rules: [
            {
                test: /\.js$/, // Processa arquivos .js
                exclude: /node_modules/, // Ignora a pasta node_modules
                use: {
                    loader: 'babel-loader',
                },
            },
        ],
    },
};