/*
 * Único arquivo que fala com a API do agente. Nenhum outro componente faz
 * fetch direto — tudo passa por aqui, pra manter os caminhos e formatos da
 * API num lugar só.
 */

const URL_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem)
    this.status = status
  }
}

async function tratarResposta(resposta) {
  if (resposta.ok) {
    return resposta.status === 204 ? null : resposta.json()
  }

  if (resposta.status === 401) {
    throw new ErroApi('Sua sessão expirou. Faça login novamente.', 401)
  }
  if (resposta.status === 404) {
    throw new ErroApi('Não encontramos o que você pediu.', 404)
  }

  let detalhe = ''
  try {
    const corpo = await resposta.json()
    detalhe = typeof corpo.detail === 'string' ? corpo.detail : ''
  } catch {
    // resposta sem corpo JSON — segue sem detalhe extra
  }
  throw new ErroApi(
    detalhe || 'O servidor não conseguiu processar seu pedido. Tente novamente em instantes.',
    resposta.status
  )
}

async function chamarApi(caminho, opcoes = {}) {
  let resposta
  try {
    resposta = await fetch(`${URL_BASE}${caminho}`, opcoes)
  } catch {
    throw new ErroApi('Não foi possível conectar ao servidor. Verifique sua internet e tente novamente.')
  }
  return tratarResposta(resposta)
}

export async function login(usuario, senha) {
  const corpo = new URLSearchParams({ username: usuario, password: senha })
  const dados = await chamarApi('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: corpo,
  })
  return dados.access_token
}

export async function buscarPerfil(token) {
  return chamarApi('/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function enviarPergunta(token, pergunta, conversaId) {
  return chamarApi('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ pergunta, conversa_id: conversaId ?? null }),
  })
}

export async function listarConversas(token) {
  return chamarApi('/conversas', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function buscarConversa(token, conversaId) {
  return chamarApi(`/conversas/${conversaId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function esqueciSenha(usuario) {
  return chamarApi('/esqueci-senha', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario }),
  })
}

export async function redefinirSenha(token, novaSenha) {
  return chamarApi('/redefinir-senha', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, nova_senha: novaSenha }),
  })
}

export { ErroApi }
