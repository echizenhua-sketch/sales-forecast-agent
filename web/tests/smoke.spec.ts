import { expect, test } from 'playwright/test';

test('login page renders the forecast agent shell', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login-v2\.html$/);
  await expect(page.getByRole('heading', { name: '产销预测 Agent' })).toBeVisible();
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
});

test('static login redirects to dashboard-v2 after successful auth', async ({ page }) => {
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        user: { id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' },
      }),
    });
  });

  await page.goto('/');
  await page.locator('#username').fill('planner');
  await page.locator('#password').fill('planner123');
  await page.getByRole('button', { name: '登录' }).click();
  await expect(page).toHaveURL(/\/dashboard-v2\.html$/);
  await expect(page.getByRole('heading', { name: '产销预测 Agent' })).toBeVisible();
  await expect(page.getByText('上传产销预测及供应表')).toBeVisible();
});

test('assistant has a dedicated sidebar page with mapped questions', async ({ page }) => {
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 4,
          file_name: '产销预测及供应表.xlsx',
          status: 'SUCCESS',
          created_at: '2026-06-21T17:18:46',
        },
      ]),
    });
  });

  await page.route('**/api/tasks/4/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_supply: 897369,
        total_sar: 900118,
        total_gap: -2749,
        service_level: 88.32,
        target_service_level: 98,
        critical_risk_count: 3,
        high_risk_count: 0,
        medium_risk_count: 1,
      }),
    });
  });

  let chatPayload: { message?: string; task_id?: number } | undefined;
  await page.route('**/api/chat', async (route) => {
    chatPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: '664116 缺口最大，建议优先排产。',
        type: 'llm_generate',
        model: 'minimax-m3',
      }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' }),
    );
  });

  await page.goto('/dashboard-v2.html');
  await expect(page.getByRole('link', { name: /智能助手/ })).toBeVisible();
  await expect(page.locator('#aiFloatingBtn')).toHaveCount(0);

  await page.getByRole('link', { name: /智能助手/ }).click();
  await expect(page).toHaveURL(/\/assistant-v2\.html$/);
  await expect(page.getByRole('heading', { name: '智能助手' })).toBeVisible();
  await expect(page.getByRole('button', { name: '分析当前风险最高的 SKU' })).toBeVisible();
  await expect(page.locator('#taskIdLabel')).toHaveText('4');
  await expect(page.getByRole('button', { name: '分析当前风险最高的 SKU' })).toBeEnabled();

  await page.getByRole('button', { name: '分析当前风险最高的 SKU' }).click();
  await expect(page.getByText('664116 缺口最大')).toBeVisible();
  expect(chatPayload?.message).toBe('分析当前风险最高的 SKU');
  expect(chatPayload?.task_id).toBe(4);
});

test('assistant keeps page fixed and scrolls only the conversation area', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 4,
          file_name: '产销预测及供应表.xlsx',
          status: 'SUCCESS',
          created_at: '2026-06-21T17:18:46',
        },
      ]),
    });
  });
  await page.route('**/api/chat', async (route) => {
    const longMessage = Array.from({ length: 80 }, (_, index) => `第 ${index + 1} 行：SKU 风险分析内容`).join('\n');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: longMessage,
        type: 'llm_generate',
        model: 'minimax-m3',
      }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' }),
    );
  });

  await page.goto('/assistant-v2.html');
  await expect(page.locator('#taskIdLabel')).toHaveText('4');
  await page.getByRole('button', { name: '分析当前风险最高的 SKU' }).click();
  await expect(page.getByText('第 80 行：SKU 风险分析内容')).toBeVisible();

  const scrollState = await page.evaluate(() => {
    const main = document.querySelector('main');
    const messages = document.querySelector('#aiMessages');
    return {
      bodyHasVerticalScroll: document.documentElement.scrollHeight > window.innerHeight,
      mainCanScroll: main ? main.scrollHeight > main.clientHeight : null,
      messagesCanScroll: messages ? messages.scrollHeight > messages.clientHeight : null,
      messagesScrollTop: messages ? messages.scrollTop : null,
    };
  });

  expect(scrollState.bodyHasVerticalScroll).toBe(false);
  expect(scrollState.mainCanScroll).toBe(false);
  expect(scrollState.messagesCanScroll).toBe(true);
  expect(scrollState.messagesScrollTop).toBeGreaterThan(0);
});

test('assistant disables send actions while answer is pending', async ({ page }) => {
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 4,
          file_name: '产销预测及供应表.xlsx',
          status: 'SUCCESS',
          created_at: '2026-06-21T17:18:46',
        },
      ]),
    });
  });

  let chatCalls = 0;
  let releaseChat: (() => void) | undefined;
  await page.route('**/api/chat', async (route) => {
    chatCalls += 1;
    await new Promise<void>((resolve) => {
      releaseChat = resolve;
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: '第一轮回答完成',
        type: 'llm_generate',
        model: 'minimax-m3',
      }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' }),
    );
  });

  await page.goto('/assistant-v2.html');
  await expect(page.locator('#taskIdLabel')).toHaveText('4');

  await page.locator('#aiInput').fill('第一轮问题');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.locator('#aiSendBtn')).toBeDisabled();
  await expect(page.locator('#aiInput')).toBeDisabled();
  await expect(page.getByRole('button', { name: '分析当前风险最高的 SKU' })).toBeDisabled();

  await page.locator('#aiInput').evaluate((input) => {
    const element = input as HTMLInputElement;
    element.disabled = false;
    element.value = '第二轮问题';
    element.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', bubbles: true }));
  });
  await page.getByRole('button', { name: '分析当前风险最高的 SKU' }).evaluate((button) => {
    const element = button as HTMLButtonElement;
    element.disabled = false;
    element.click();
  });

  await expect.poll(() => chatCalls).toBe(1);
  releaseChat?.();
  await expect(page.getByText('第一轮回答完成')).toBeVisible();
  await expect(page.locator('#aiSendBtn')).toBeEnabled();
  await expect(page.locator('#aiInput')).toBeEnabled();
  await expect(page.getByRole('button', { name: '分析当前风险最高的 SKU' })).toBeEnabled();
});

test('assistant loads conversation history and continues the selected session', async ({ page }) => {
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 4,
          file_name: '产销预测及供应表.xlsx',
          status: 'SUCCESS',
          created_at: '2026-06-21T17:18:46',
        },
      ]),
    });
  });
  await page.route('**/api/chat/sessions?task_id=4', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          session_id: 'history-session',
          task_id: 4,
          title: '第一轮问题',
          last_question: '第一轮问题',
          last_answer: '第一轮回答',
          message_count: 1,
          updated_at: '2026-06-21T17:20:00',
        },
      ]),
    });
  });
  await page.route('**/api/chat/sessions/history-session', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session_id: 'history-session',
        task_id: 4,
        title: '第一轮问题',
        message_count: 1,
        messages: [
          {
            id: 1,
            question: '第一轮问题',
            answer: '第一轮回答',
            created_at: '2026-06-21T17:20:00',
          },
        ],
      }),
    });
  });

  let chatPayload: { message?: string; task_id?: number; session_id?: string } | undefined;
  await page.route('**/api/chat', async (route) => {
    chatPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: '继续回答',
        conversation_id: 2,
        session_id: chatPayload?.session_id,
        type: 'llm_generate',
        model: 'minimax-m3',
      }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' }),
    );
  });

  await page.goto('/assistant-v2.html');
  await expect(page.getByText('对话历史')).toBeVisible();
  await expect(page.getByRole('button', { name: /第一轮问题/ })).toBeVisible();

  await page.getByRole('button', { name: /第一轮问题/ }).click();
  await expect(page.getByText('第一轮回答')).toBeVisible();

  await page.locator('#aiInput').fill('继续分析');
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('继续回答')).toBeVisible();
  expect(chatPayload?.session_id).toBe('history-session');
  expect(chatPayload?.task_id).toBe(4);
  expect(chatPayload?.message).toBe('继续分析');
});

test('assistant refreshes history when model response is saved but unsuccessful', async ({ page }) => {
  let historyCalls = 0;
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 4,
          file_name: '产销预测及供应表.xlsx',
          status: 'SUCCESS',
          created_at: '2026-06-21T17:18:46',
        },
      ]),
    });
  });
  await page.route('**/api/chat/sessions?task_id=4', async (route) => {
    historyCalls += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(
        historyCalls === 1
          ? []
          : [
              {
                session_id: 'saved-error-session',
                task_id: 4,
                title: '模型失败也要入历史',
                last_question: '模型失败也要入历史',
                last_answer: '模型调用失败：账号池不可用',
                message_count: 1,
                updated_at: '2026-06-21T17:20:00',
              },
            ],
      ),
    });
  });
  await page.route('**/api/chat', async (route) => {
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        message: '模型调用失败：账号池不可用',
        conversation_id: 9,
        session_id: payload.session_id,
        type: 'llm_error',
        model: 'minimax-m3',
      }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'planner', real_name: '陈计划', role: 'PLANNER' }),
    );
  });

  await page.goto('/assistant-v2.html');
  await expect(page.getByText('暂无历史对话')).toBeVisible();

  await page.locator('#aiInput').fill('模型失败也要入历史');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.getByText('模型调用失败：账号池不可用')).toBeVisible();
  await expect(page.getByRole('button', { name: /模型失败也要入历史/ })).toBeVisible();
  expect(historyCalls).toBeGreaterThanOrEqual(2);
});

test('results page exports excel through backend endpoint', async ({ page }) => {
  await page.route('**/api/tasks', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 9, file_name: '产销预测及供应表.xlsx', status: 'SUCCESS', created_at: '2026-06-21T17:18:46' }]),
    });
  });
  await page.route('**/api/tasks/9/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total_supply: 100, total_sar: 120, total_gap: -20, service_level: 80, target_service_level: 98, critical_risk_count: 1, high_risk_count: 0, medium_risk_count: 0 }),
    });
  });
  await page.route('**/api/tasks/9/sku-details?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: 1, page: 1, page_size: 50, items: [{ sku_code: 'SKU-002', product_name: '测试SKU', total_supply: 100, sar_total: 120, gap: -20, service_level: 80, risk_level: 'CRITICAL' }] }),
    });
  });
  let exportCalled = false;
  await page.route('**/api/tasks/9/export?**', async (route) => {
    exportCalled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      body: 'fake-xlsx',
    });
  });
  await page.addInitScript(() => {
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', real_name: '系统管理员', role: 'ADMIN' }));
    localStorage.setItem('accessToken', 'test-token');
  });

  await page.goto('/results-v2.html?taskId=9');
  await page.getByRole('button', { name: /导出Excel/ }).click();
  await expect.poll(() => exportCalled).toBeTruthy();
});

test('logs and settings pages render backend data', async ({ page }) => {
  await page.route('**/api/logs?limit=100', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [{ id: 1, username: 'admin', operation: 'EXPORT', resource_type: 'TASK', resource_id: 9, detail: { file_name: '导出.xlsx' }, created_at: '2026-06-21T17:18:46' }] }),
    });
  });
  await page.route('**/api/settings', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [{ key: 'file.max_size', value: '52428800', type: 'NUMBER', description: '文件上传大小上限' }] }),
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', real_name: '系统管理员', role: 'ADMIN' }));
    localStorage.setItem('accessToken', 'test-token');
  });

  await page.goto('/logs-v2.html');
  await expect(page.getByRole('heading', { name: '操作日志' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '产销预测 Agent' })).toBeVisible();
  await expect(page.getByRole('link', { name: /操作日志/ })).toHaveClass(/bg-primary-container/);
  await expect(page.getByPlaceholder('搜索预测结果或任务...')).toBeVisible();
  await expect(page.getByText('日志明细')).toBeVisible();
  await expect(page.getByText('导出', { exact: true })).toBeVisible();
  await expect(page.getByText('导出操作')).toBeVisible();

  await page.goto('/settings-v2.html');
  await expect(page.getByRole('heading', { name: '系统设置' })).toBeVisible();
  await expect(page.getByText('file.max_size')).toBeVisible();
});

test('processing page polls real task status and opens result page', async ({ page }) => {
  let calls = 0;
  await page.route('**/api/tasks/12', async (route) => {
    calls += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 12,
        file_name: '产销预测及供应表.xlsx',
        file_size: 31264,
        status: calls >= 2 ? 'SUCCESS' : 'CALCULATING',
        progress: calls >= 2 ? 100 : 60,
        created_at: '2026-06-21T17:18:46',
        updated_at: '2026-06-21T17:18:48',
      }),
    });
  });

  await page.goto('/processing.html?taskId=12');
  await expect(page.getByText('产销预测及供应表.xlsx')).toBeVisible();
  await expect(page.getByRole('button', { name: '查看结果' })).toBeEnabled();
  await page.getByRole('button', { name: '查看结果' }).click();
  await expect(page).toHaveURL(/results-v2\.html\?taskId=12$/);
});
