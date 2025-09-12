class PriceDashboard {
    constructor() {
        this.currentData = null;
        this.historyData = null;
        this.init();
    }

    async init() {
        try {
            await this.loadData();
            this.renderSummary();
            this.renderProducts();
            this.renderChart();
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showError();
        }
    }

    async loadData() {
        const [currentResponse, historyResponse] = await Promise.all([
            fetch('data/current-prices.json'),
            fetch('data/price-history.json')
        ]);

        this.currentData = await currentResponse.json();
        this.historyData = await historyResponse.json();
    }

    renderSummary() {
        const products = this.currentData.products || [];
        const alerts = products.filter(p => p.current_price <= p.target_price);
        const savings = alerts.reduce((sum, p) => sum + (p.target_price - p.current_price), 0);

        document.getElementById('total-products').textContent = products.length;
        document.getElementById('active-alerts').textContent = alerts.length;
        document.getElementById('potential-savings').textContent = `€${savings.toFixed(2)}`;
        document.getElementById('last-update').textContent = 
            `Última actualización: ${new Date(this.currentData.last_update).toLocaleString('es-ES')}`;
    }

    renderProducts() {
        const container = document.getElementById('products-grid');
        const products = this.currentData.products || [];

        container.innerHTML = products.map(product => `
            <div class="product-card ${product.current_price <= product.target_price ? 'alert' : ''}">
                <div class="product-header">
                    <h4>${product.name}</h4>
                    <span class="status ${product.current_price <= product.target_price ? 'target-reached' : 'waiting'}">
                        ${product.current_price <= product.target_price ? '🎉 ¡Objetivo!' : '⏳ Esperando'}
                    </span>
                </div>
                
                <div class="prices">
                    <div class="current-price">
                        <span>Precio actual</span>
                        <strong>€${product.current_price || 'N/A'}</strong>
                    </div>
                    <div class="target-price">
                        <span>Precio objetivo</span>
                        <strong>€${product.target_price}</strong>
                    </div>
                </div>

                <div class="price-diff">
                    ${product.current_price ? 
                        (product.current_price <= product.target_price ? 
                            `<span class="savings">💰 Ahorras €${(product.target_price - product.current_price).toFixed(2)}</span>` :
                            `<span class="waiting">📊 Faltan €${(product.current_price - product.target_price).toFixed(2)}</span>`
                        ) : 
                        '<span class="error">❌ Precio no disponible</span>'
                    }
                </div>

                <div class="actions">
                    <a href="${product.url}" target="_blank" class="btn btn-primary">Ver en Amazon</a>
                    <button onclick="dashboard.showHistory('${product.name}')" class="btn btn-secondary">📈 Historial</button>
                </div>
            </div>
        `).join('');
    }

    renderChart() {
        const ctx = document.getElementById('price-chart').getContext('2d');
        const history = this.historyData.history || {};
        
        // Procesar datos para el gráfico
        const datasets = Object.keys(history).map((productName, index) => ({
            label: productName,
            data: history[productName].map(entry => ({
                x: entry.date,
                y: entry.price
            })),
            borderColor: this.getColor(index),
            backgroundColor: this.getColor(index, 0.1),
            tension: 0.4
        }));

        new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Evolución de Precios'
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day'
                        }
                    },
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: value => `€${value}`
                        }
                    }
                }
            }
        });
    }

    getColor(index, alpha = 1) {
        const colors = [
            `rgba(255, 99, 132, ${alpha})`,
            `rgba(54, 162, 235, ${alpha})`,
            `rgba(255, 205, 86, ${alpha})`,
            `rgba(75, 192, 192, ${alpha})`,
            `rgba(153, 102, 255, ${alpha})`,
            `rgba(255, 159, 64, ${alpha})`
        ];
        return colors[index % colors.length];
    }

    showHistory(productName) {
        // Modal simple para mostrar historial detallado
        alert(`Historial detallado de ${productName} - Próximamente implementado`);
    }

    showError() {
        document.body.innerHTML = `
            <div class="error-container">
                <h2>❌ Error al cargar datos</h2>
                <p>No se pudieron cargar los datos del monitor. Esto puede suceder si:</p>
                <ul>
                    <li>Es la primera ejecución del sistema</li>
                    <li>GitHub Actions aún no ha generado los archivos</li>
                    <li>Hay un problema con la configuración</li>
                </ul>
                <button onclick="location.reload()">🔄 Reintentar</button>
            </div>
        `;
    }
}

// Inicializar dashboard cuando se carga la página
const dashboard = new PriceDashboard();