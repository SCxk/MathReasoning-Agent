"""UI upload/retrieval exercise using actual offline Qwen and Qdrant."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8003')
    parser.add_argument('--output-dir',type=Path,default=Path('sample_outputs/platform_m5/ui'))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge',headless=True)
        for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
            page = browser.new_page(viewport={'width':width,'height':height})
            errors = []
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(args.url)
            page.wait_for_function("document.getElementById('session-id').textContent.length === 36")
            assert page.locator('#document-section').is_visible()
            page.locator('#document-file').set_input_files({'name':'polynomial.md','mimeType':'',
                'buffer':b'# Polynomial identity\n$$ (a+b)^2 = a^2 + 2ab + b^2 $$'})
            page.locator('#document-domain').fill('algebra')
            page.locator('#document-source').fill('browser functional fixture')
            page.locator('#document-upload').click()
            page.wait_for_function("document.getElementById('document-list').textContent.includes('可检索')",timeout=60000)
            assert not page.locator('#error').is_visible()
            page.locator('#problem').fill('Find relevant passages about the polynomial identity (a+b)^2.')
            page.locator('#submit').click()
            page.wait_for_function("!document.getElementById('answer').hidden",timeout=60000)
            assert 'Fake Runtime completed' in page.locator('#answer').inner_text()
            page.locator('#json-tab').click()
            trace = json.loads(page.locator('#raw-trace').inner_text())
            retrieval = [event for event in trace if event['event_type'] == 'retrieval.completed']
            assert retrieval[0]['payload']['hit_count'] == 1
            assert retrieval[0]['payload']['references'][0]['source_metadata']['title'] == 'polynomial.md'
            assert retrieval[0]['payload']['status'] == 'retrieved_not_used_by_fake_runtime'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#events-tab').click()
            page.screenshot(path=str(args.output_dir/f'{name}-complete.png'),full_page=True)
            page.locator('#new-session').click()
            page.wait_for_function("document.getElementById('document-list').children.length === 0")
            assert page.locator('#document-file').input_value() == ''
            assert not errors,errors
            print(json.dumps({'viewport':name,'status':'passed','browser_errors':errors,
                              'real_retrieval':True,'answer_quality':'not_measured'}))
            page.close()
        browser.close()


if __name__ == '__main__':
    main()
