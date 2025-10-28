import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/vue'
import { afterEach, vi } from 'vitest'
import createFetchMock from 'vitest-fetch-mock'

const fetchMock = createFetchMock(vi)
fetchMock.enableMocks()

afterEach(() => {
  cleanup()
  fetchMock.resetMocks()
})
