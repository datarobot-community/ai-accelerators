import { test, expect } from '@playwright/test';
const TIMEOUT = 5 * 60 * 1000;

test.describe('Logged in tests', () => {
    let context;
    let page;

    test.beforeAll(async ({browser}) => {
        context = await browser.newContext({
            serviceWorkers: 'block',
        });
        page = await context.newPage();

        await page.goto('http://localhost:5173/', {
            waitUntil: 'networkidle',
        });
    });

    test.afterAll(async () => {
        await context?.close();
    });

    test('start new chat', async () => {
        await page.getByTestId('start-new-chat-btn').click();
        await expect(page.getByText('Assistant')).toBeVisible();
        await expect(page.getByText('Hi. Here you can test your agent-based application.')).toBeVisible();
    });

    test('write a question to agent and wait until response fully done', async () => {
        test.setTimeout(TIMEOUT); // to wait long response from agent

        await page.getByTestId('start-new-chat-btn').click();
        await page.getByRole('textbox').fill('tell me small story');

        await page.getByTestId('send-message-btn').click();
        const spinner = await page.getByTestId('thinking-loading')
        await expect(spinner).toBeVisible();
        await expect(page.getByTestId('send-message-disabled-btn')).toBeDisabled()

        // wait until message will be received
        await page.getByTestId('send-message-btn').waitFor({ state: 'visible', timeout: TIMEOUT });
    });

    test('new thread is active when user switches chats', async () => {
        let contentCount = 0
        let prevContentCount;
        await page.getByTestId('start-new-chat-btn').click();

        await page.getByRole('textbox').fill('tell some fun fact');
        await page.getByTestId('send-message-btn').click();

        await expect.poll(
            async () => {
                const content = await page.locator('[data-testid^="default-assistant-message-"]')?.first();
                const text = await content.textContent();
                contentCount =  text?.length ?? 0;
                return contentCount;
            },
            {
                timeout: TIMEOUT,
            }
        ).toBeGreaterThan(0);

        await page.locator('#sidebar-chats').locator('[data-testid^="chat-"]')?.last().click();
        await expect(page.getByTestId('send-message-btn')).toBeVisible();

        await page.locator('#sidebar-chats').locator('[data-testid^="chat-"]')?.first().click();

        prevContentCount = contentCount;
        await expect.poll(
            async () => {
                const content = await page.locator('[data-testid^="default-assistant-message-"]')?.first();
                const text = await content.textContent();
                contentCount =  text?.length ?? 0;
                return contentCount;
            },
            {
                timeout: TIMEOUT,
            }
        ).toBeGreaterThan(prevContentCount);


    })

    test('remove all chats', async () => {
        await page.locator('#sidebar-chats').locator('[data-testid^="chat-"]')?.last().click();
        const oldUrl = page.url();
        await page.locator('.dropdown-menu-trigger')?.last().click();
        await page.getByTestId('delete-chat-menu-item').click();
        await expect.poll(() => page.url()).not.toBe(oldUrl); // user was redirected to the active chat

        await page.locator('#sidebar-chats').locator('[data-testid^="chat-"]')?.first().click();

        // wait until message will be received
        await page.getByTestId('send-message-btn').waitFor({ state: 'visible', timeout: TIMEOUT });
        await page.locator('.dropdown-menu-trigger')?.last().click();
        await page.getByTestId('delete-chat-menu-item').click();

        await expect(page.getByText('Hi. Here you can test your agent-based application.')).toBeVisible();
    })
})
