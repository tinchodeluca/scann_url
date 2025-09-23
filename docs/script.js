class PriceDashboard {
    constructor() {
        this.currentData = null;
        this.historyData = null;
        this.init();
    }

    async init() {
        console.log("🚀 Iniciando dashboard...");
        try {
            await this.loadData();
            this.renderSummary();
            this.renderProducts();
            this.renderChart();
            console.log("✅ Dashboard cargado correctamente");
        } catch (error) {
            console.error('❌ Error loading dashboard:', error);
            this.showError(error.message);
        }
    }

    async loadData() {
        console.log("📥 Cargando datos...");
        
        try {
            console.log("📄 Cargando current-prices.json...");
            const currentResponse = await fetch('./data/current-prices.json');
            
            if (!currentResponse.ok) {
                throw new Error(`Error cargando current-prices.json: ${currentResponse.status}`);
            }
            
            this.currentData = await currentResponse.json();
            console.log("✅ current-prices.json cargado:", this.currentData);
            
            console.log("📄 Cargando price-history.json...");
            const historyResponse = await fetch('./data/price-history.json');
            
            if (!historyResponse.ok) {
                throw new Error(`Error cargando price-history.json: ${historyResponse.status}`);
            }
            
            this.historyData = await historyResponse.json();
            console.log("✅ price-history.json cargado:", this.historyData);
            
        } catch (error) {
            console.error("❌ Error en loadData:", error);
            throw error;
        }
    }

    renderSummary() {
        console.log("📊 Renderizando resumen...");
        
        const products = this.currentData.products || [];
        const alerts = products.filter(p => p.alert === true);
        const savings = this.currentData.total_savings || 0;

        document.getElementById('total-products').textContent = products.length;
        document.getElementById('active-alerts').textContent = alerts.length;
        document.getElementById('potential-savings').textContent = `€${savings.toFixed(2)}`;
        
        const lastUpdate = new Date(this.currentData.last_update);
        document.getElementById('last-update').textContent = 
            `Última actualización: ${lastUpdate.toLocaleString('es-ES')}`;

        console.log(`📈 Resumen: ${products.length} productos, ${alerts.length} alertas, €${savings} ahorros`);
    }

    renderProducts() {
        console.log("🛍️ Renderizando productos...");
        
        const container = document.getElementById('products-grid');
        const products = this.currentData.products || [];

        if (products.length === 0) {
            container.innerHTML = `
                <div class="no-products">
                    <h3>📦 No hay productos configurados</h3>
                    <p>Agrega productos al archivo config.json para empezar a monitorear precios.</p>
                </div>
            `;
            return;
        }

        const productsHTML = products.map(product => {
            const savings = product.alert ? (product.target_price - product.current_price) : 0;
            const difference = product.current_price ? (product.current_price - product.target_price) : 0;
            
            return `
                <div class="product-card ${product.alert ? 'alert' : ''}">
                    <div class="product-header">
                        <h4 title="${product.name}">${this.truncateText(product.name, 60)}</h4>
                        <span class="status ${product.alert ? 'target-reached' : 'waiting'}">
                            ${product.alert ? '🎉 ¡Objetivo!' : '⏳ Esperando'}
                        </span>
                    </div>
                    
                    <div class="prices">
                        <div class="current-price">
                            <span>Precio actual</span>
                            <strong>${product.current_price ? `€${product.current_price.toFixed(2)}` : 'N/A'}</strong>
                        </div>
                        <div class="target-price">
                            <span>Precio objetivo</span>
                            <strong>€${product.target_price.toFixed(2)}</strong>
                        </div>
                    </div>

                    <div class="price-diff">
                        ${product.current_price ? 
                            (product.alert ? 
                                `<span class="savings">💰 Ahorras €${savings.toFixed(2)}</span>` :
                                `<span class="waiting">📊 Faltan €${difference.toFixed(2)}</span>`
                            ) : 
                            '<span class="error">❌ Precio no disponible</span>'
                        }
                    </div>

                    <div class="actions">
                        <a href="${product.url}" target="_blank" class="btn btn-primary">Ver en Amazon</a>
                        <button onclick="dashboard.showHistory('${product.name}')" class="btn btn-secondary">📈 Historial</button>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = productsHTML;
        console.log(`✅ ${products.length} productos renderizados`);
    }

    renderChart() {
        console.log("📈 Renderizando gráfico...");
        
        // Verificar si Chart.js está disponible
        if (typeof Chart === 'undefined') {
            console.warn("⚠️ Chart.js no está disponible, saltando gráfico");
            document.querySelector('.charts-section').innerHTML = `
                <h2>📈 Evolución de Precios</h2>
                <div class="no-data">
                    <h3>📊 Gráfico no disponible</h3>
                    <p>Chart.js no se pudo cargar.</p>
                </div>
            `;
            return;
        }

        const ctx = document.getElementById('price-chart');
        if (!ctx) {
            console.warn("⚠️ Elemento price-chart no encontrado");
            return;
        }

        const history = this.historyData.history || {};
        
        if (Object.keys(history).length === 0) {
            ctx.parentElement.innerHTML = `
                <div class="no-data">
                    <h3>📈 Sin datos de historial</h3>
                    <p>Los datos del historial se generarán después de varias ejecuciones del monitor.</p>
                </div>
            `;
            return;
        }

        // Procesar datos para el gráfico
        const datasets = Object.keys(history).map((productName, index) => ({
            label: this.truncateText(productName, 30),
            data: history[productName].map(entry => ({
                x: entry.date,
                y: entry.price
            })),
            borderColor: this.getColor(index),
            backgroundColor: this.getColor(index, 0.1),
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6
        }));

        try {
            new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Evolución de Precios (Últimos 30 días)',
                            font: { size: 16 }
                        },
                        legend: {
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 20
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'dd/MM'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Fecha'
                            }
                        },
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Precio (€)'
                            },
                            ticks: {
                                callback: value => `€${value}`
                            }
                        }
                    }
                }
            });
            console.log("✅ Gráfico renderizado");
        } catch (error) {
            console.error("❌ Error renderizando gráfico:", error);
        }
    }

    getColor(index, alpha = 1) {
        const colors = [
            `rgba(102, 126, 234, ${alpha})`,  // Azul
            `rgba(255, 99, 132, ${alpha})`,   // Rojo
            `rgba(75, 192, 192, ${alpha})`,   // Verde
            `rgba(255, 205, 86, ${alpha})`,   // Amarillo
            `rgba(153, 102, 255, ${alpha})`,  // Púrpura
            `rgba(255, 159, 64, ${alpha})`,   // Naranja
        ];
        return colors[index % colors.length];
    }

    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    showHistory(productName) {
        const history = this.historyData.history[productName] || [];
        if (history.length === 0) {
            alert(`No hay historial disponible para "${productName}"`);
            return;
        }

        const historyText = history.slice(-10).map(entry => 
            `${new Date(entry.date).toLocaleDateString('es-ES')}: €${entry.price.toFixed(2)}`
        ).join('\n');

        alert(`Historial de precios para "${productName}":\n\n${historyText}\n\n(Últimos 10 registros)`);
    }

    showError(errorMessage = "Error desconocido") {
        console.error("💥 Mostrando error:", errorMessage);
        
        document.body.innerHTML = `
            <div class="error-container">
                <h2>❌ Error al cargar datos</h2>
                <p>No se pudieron cargar los datos del monitor.</p>
                <details>
                    <summary>Detalles técnicos</summary>
                    <p><strong>Error:</strong> ${errorMessage}</p>
                    <p><strong>Soluciones posibles:</strong></p>
                    <ul>
                        <li>Verificar que los archivos JSON existan</li>
                        <li>Ejecutar el monitor en GitHub Actions</li>
                        <li>Revisar la consola del navegador (F12)</li>
                    </ul>
                </details>
                <div class="error-actions">
                    <button onclick="location.reload()" class="btn btn-primary">🔄 Reintentar</button>
                    <a href="https://github.com/tinchodeluca/scann_url" class="btn btn-secondary">📝 Ver repositorio</a>
                </div>
            </div>
        `;
    }
}

// Inicializar dashboard cuando se carga la página
let dashboard;

document.addEventListener('DOMContentLoaded', () => {
    console.log("🌐 DOM cargado, iniciando dashboard...");
    dashboard = new PriceDashboard();
});

// Logging para debug
window.addEventListener('error', (event) => {
    console.error('💥 Error global:', event.error);
});

console.log("📜 Script del dashboard cargado");