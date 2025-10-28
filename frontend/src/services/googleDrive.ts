import type { DocumentItem } from '@/types/graph'

declare global {
  interface Window {
    gapi: any
    google: any
  }
}

export interface GoogleDocMetadata {
  id: string
  name: string
  mimeType: string
  modifiedTime: string
  owner?: string
  url?: string
  iconLink?: string
}

export interface GoogleUser {
  id: string
  email: string
  name: string
}

const DRIVE_SCOPES = [
  'https://www.googleapis.com/auth/drive.readonly',
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile'
].join(' ')

const GAPI_SCRIPT_SRC = 'https://apis.google.com/js/api.js'
const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

let googleUser: GoogleUser | null = null
let gapiLoaded = false
let clientInitialized = false
let useMock = import.meta.env.VITE_USE_MOCK_GOOGLE === 'true'
let gisLoaded = false
let tokenClient: any = null
let accessToken: string | null = null

export function getCurrentGoogleUser(): GoogleUser | null {
  return googleUser
}

export async function fetchDriveDocuments(): Promise<GoogleDocMetadata[]> {
  if (useMock) {
    return createMockDocuments()
  }

  await ensureAuthenticated()

  const response = await window.gapi.client.drive.files.list({
    pageSize: 10,
    corpora: 'user',
    orderBy: 'modifiedTime desc',
    fields: 'files(id,name,mimeType,modifiedTime,owners(displayName),webViewLink,iconLink)'
  })

  const files = response.result.files ?? []
  return files.map((file: any) => ({
    id: file.id,
    name: file.name,
    mimeType: file.mimeType,
    modifiedTime: file.modifiedTime,
    owner: file.owners?.[0]?.displayName,
    url: file.webViewLink,
    iconLink: file.iconLink
  }))
}

export async function ensureAuthenticated(): Promise<GoogleUser> {
  if (useMock) {
    googleUser = {
      id: 'mock-user',
      email: 'demo@example.com',
      name: 'Demo User'
    }
    return googleUser
  }

  await initDriveClient()

  if (!accessToken) {
    try {
      accessToken = await requestAccessToken(false)
    } catch (error) {
      accessToken = await requestAccessToken(true)
    }
  }

  if (!googleUser) {
    googleUser = await fetchUserProfile()
  }

  return googleUser
}

async function initDriveClient() {
  if (clientInitialized) return
  await loadGapiScript()
  await loadGisScript()

  await new Promise<void>((resolve, reject) => {
    window.gapi.load('client', {
      callback: () => resolve(),
      onerror: () => reject(new Error('Failed to load Google APIs')),
      timeout: 5000,
      ontimeout: () => reject(new Error('Loading Google APIs timed out'))
    })
  })

  const clientId = getRequiredEnv('VITE_GOOGLE_CLIENT_ID')
  const apiKey = getRequiredEnv('VITE_GOOGLE_API_KEY')

  await window.gapi.client.init({
    apiKey,
    discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest']
  })

  tokenClient = window.google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: DRIVE_SCOPES,
    callback: () => {}
  })

  clientInitialized = true
}

async function loadGapiScript(): Promise<void> {
  if (gapiLoaded) return
  if (typeof window === 'undefined') {
    throw new Error('Google APIs can only be loaded in the browser.')
  }

  await new Promise<void>((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[src=\"${GAPI_SCRIPT_SRC}\"]`
    )
    if (existingScript) {
      existingScript.addEventListener('load', () => {
        gapiLoaded = true
        resolve()
      })
      existingScript.addEventListener('error', () =>
        reject(new Error('Failed to load Google API script'))
      )
      return
    }

    const script = document.createElement('script')
    script.src = GAPI_SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = () => {
      gapiLoaded = true
      resolve()
    }
    script.onerror = () => reject(new Error('Failed to load Google API script'))
    document.head.appendChild(script)
  })
}

async function loadGisScript(): Promise<void> {
  if (gisLoaded || useMock) return
  await loadScript(GIS_SCRIPT_SRC)
  gisLoaded = true
}

function createMockDocuments(): GoogleDocMetadata[] {
  return [
    {
      id: `mock-gdoc-${Date.now()}`,
      name: 'Market Analysis Q1',
      mimeType: 'application/vnd.google-apps.document',
      modifiedTime: new Date().toISOString(),
      owner: 'Demo User',
      url: 'https://docs.google.com/document/d/mock',
      iconLink: 'https://ssl.gstatic.com/docs/doclist/images/mediatype/icon_1_document_x16.png'
    }
  ]
}

function getRequiredEnv(key: string): string {
  const value = import.meta.env[key]
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`)
  }
  return value
}

async function fetchUserProfile(): Promise<GoogleUser> {
  if (!accessToken) {
    throw new Error('Access token not available')
  }

  const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  })

  if (!response.ok) {
    throw new Error('Failed to fetch Google user profile')
  }

  const data = await response.json()
  return {
    id: data.sub,
    email: data.email,
    name: data.name ?? data.email
  }
}

function requestAccessToken(forcePrompt: boolean): Promise<string> {
  if (!tokenClient) {
    throw new Error('Token client not initialised')
  }

  return new Promise((resolve, reject) => {
    tokenClient.callback = (response: any) => {
      if (response.error !== undefined) {
        reject(response)
        return
      }
      const token = response.access_token as string | undefined
      if (!token) {
        reject(new Error('No access token returned from Google Identity Services'))
        return
      }
      accessToken = token
      window.gapi.client.setToken({ access_token: token })
      resolve(token)
    }

    try {
      tokenClient.requestAccessToken({ prompt: forcePrompt ? 'consent' : '' })
    } catch (error) {
      reject(error)
    }
  })
}

async function loadScript(src: string): Promise<void> {
  if (typeof document === 'undefined') return
  const existing = document.querySelector(`script[src="${src}"]`)
  if (existing) {
    if (existing.hasAttribute('data-loaded')) {
      return
    }
    await new Promise<void>((resolve, reject) => {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error(`Failed to load script ${src}`)), {
        once: true
      })
    })
    return
  }

  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.defer = true
    script.onload = () => {
      script.setAttribute('data-loaded', 'true')
      resolve()
    }
    script.onerror = () => reject(new Error(`Failed to load script ${src}`))
    document.head.appendChild(script)
  })
}

export function formatGoogleDocDescription(doc: GoogleDocMetadata): string {
  const timestamp = new Date(doc.modifiedTime).toLocaleString()
  return `Google Drive · Last modified ${timestamp}`
}

export function toDocumentInput(doc: GoogleDocMetadata): Pick<
  DocumentItem,
  'mimeType' | 'author' | 'url' | 'externalId' | 'description'
> & { title: string } {
  return {
    title: doc.name,
    mimeType: doc.mimeType,
    author: doc.owner,
    url: doc.url,
    externalId: doc.id,
    description: formatGoogleDocDescription(doc)
  }
}
