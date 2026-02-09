/// <reference types="vitest/globals" />
import '@testing-library/jest-dom'
import { server } from './__mocks__/node.js'

beforeAll(() => {
  server.listen()
})

afterEach(() => {
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
