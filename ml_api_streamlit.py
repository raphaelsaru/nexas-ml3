import streamlit as st
import requests
import pandas as pd
import altair as alt
from urllib.parse import quote

def buscar_produtos_ml(query, offset=0, limit=50):
    """
    Busca produtos no Mercado Livre usando a API oficial
    """
    # Codifica a query para URL
    encoded_query = quote(query)
    
    # URL da API do Mercado Livre
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={encoded_query}&offset={offset}&limit={limit}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Levanta exceção para status codes de erro
        data = response.json()
        return data.get('results', [])
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar produtos: {str(e)}")
        return []

def extrair_dados_produto(produto):
    """
    Extrai informações relevantes do produto
    """
    return {
        'Nome': produto.get('title'),
        'Preço': produto.get('price'),
        'Link': produto.get('permalink'),
        'Condição': 'Novo' if produto.get('condition') == 'new' else 'Usado',
        'Frete Grátis': 'Sim' if produto.get('shipping', {}).get('free_shipping') else 'Não',
        'Vendidos': produto.get('sold_quantity', 0)
    }

def processar_busca_exata(produtos, query):
    """
    Filtra produtos para garantir que palavras entre aspas estejam presentes
    """
    import re
    
    # Encontra todas as palavras entre aspas
    termos_exatos = re.findall(r'"([^"]*)"', query)
    
    if not termos_exatos:
        return produtos
    
    # Filtra os produtos que contêm todas as palavras exatas
    produtos_filtrados = []
    for produto in produtos:
        titulo = produto.get('title', '').lower()
        if all(termo.lower() in titulo for termo in termos_exatos):
            produtos_filtrados.append(produto)
    
    return produtos_filtrados

def main():
    st.set_page_config(
        page_title="Buscador Mercado Livre",
        page_icon="🛍️",
        layout="wide"
    )
    
    st.title("🛍️ Buscador Mercado Livre")
    st.write("Digite o produto que deseja buscar e veja os resultados das 10 primeiras páginas do Mercado Livre")
    st.write("💡 Dica: Use aspas para buscar palavras exatas. Exemplo: celular \"samsung\" \"novo\"")
    
    # Campo de busca
    busca = st.text_input("O que você está procurando?")
    
    if busca:
        with st.spinner('Buscando produtos...'):
            # Busca produtos das primeiras 10 páginas
            todos_produtos = []
            for offset in range(0, 500, 50):  # 10 páginas de 50 produtos cada
                produtos = buscar_produtos_ml(busca, offset=offset)
                todos_produtos.extend(produtos)
            
            # Aplica o filtro de busca exata
            todos_produtos = processar_busca_exata(todos_produtos, busca)
            
            if todos_produtos:
                # Processa os dados dos produtos
                dados_produtos = [extrair_dados_produto(p) for p in todos_produtos]
                df = pd.DataFrame(dados_produtos)
                
                # Adiciona formatação de preço
                df['Preço Formatado'] = df['Preço'].apply(lambda x: f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
                
                # Opções de ordenação e filtros
                col1, col2, col3 = st.columns(3)
                with col1:
                    ordem = st.selectbox(
                        "Ordenar por preço:",
                        ["Menor para maior", "Maior para menor"]
                    )
                
                with col2:
                    filtro_frete = st.checkbox("Apenas frete grátis", key="frete")
                
                with col3:
                    condicao = st.multiselect(
                        "Condição do produto",
                        ["Novo", "Usado"],
                        default=["Novo", "Usado"]
                    )
                
                # Aplica filtros
                if filtro_frete:
                    df = df[df['Frete Grátis'] == 'Sim']
                
                if condicao:
                    df = df[df['Condição'].isin(condicao)]
                
                # Ordena DataFrame
                if ordem == "Menor para maior":
                    df = df.sort_values('Preço')
                else:
                    df = df.sort_values('Preço', ascending=False)
                
                # Exibe estatísticas
                st.write(f"Encontrados {len(df)} produtos")
                
                # Exibe métricas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Preço Médio", f"R$ {df['Preço'].mean():,.2f}")
                with col2:
                    st.metric("Preço Mínimo", f"R$ {df['Preço'].min():,.2f}")
                with col3:
                    st.metric("Preço Máximo", f"R$ {df['Preço'].max():,.2f}")
                
                # Exibe resultados em uma tabela interativa
                st.dataframe(
                    df[[
                        'Nome', 'Preço Formatado', 'Condição',
                        'Frete Grátis', 'Vendidos', 'Link'
                    ]],
                    column_config={
                        'Link': st.column_config.LinkColumn(),
                        'Preço Formatado': 'Preço',
                        'Vendidos': st.column_config.NumberColumn(
                            'Quantidade Vendida',
                            help='Quantidade de unidades vendidas'
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Adiciona um gráfico de distribuição de preços
                st.subheader("Distribuição de Preços")
                
                # Criar o gráfico usando Altair
                chart = alt.Chart(df).mark_bar().encode(
                    alt.X('Preço:Q', bin=alt.Bin(maxbins=30), title='Faixa de Preço (R$)'),
                    alt.Y('count()', title='Quantidade de Produtos'),
                    tooltip=['count()', alt.Tooltip('Preço:Q', format=',.2f')]
                ).properties(
                    height=300
                )
                
                st.altair_chart(chart, use_container_width=True)
                
            else:
                st.warning("Nenhum produto encontrado.")

if __name__ == "__main__":
    main()
