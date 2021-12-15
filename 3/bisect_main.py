import asyncio


async def test(command: bytes):
    left = 0
    right = 9375
    last_return_code = 1
    while left < right:
        if last_return_code:
            await (await asyncio.subprocess.create_subprocess_exec(
                'rm', '-f', 'B-TREE_FILE', ' POSTINGSFILE', 'TEXTFILE'
            )).wait()
        main_process = await asyncio.create_subprocess_exec(
            'SRC/main',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
        )

        mid = (left + right) // 2
        print(mid)
        insert_commands = b'\n'.join(f'i Datafiles/dict{i:06}'.encode('utf-8')
                                     for i in range(0 if last_return_code else left, mid + 1))
        commands = insert_commands + b'\n' + command + b'\nx'
        await main_process.communicate(commands)
        last_return_code = main_process.returncode
        if main_process.returncode:
            right = mid
        else:
            left = mid + 1
    return right

if __name__ == '__main__':
    print(asyncio.run(test(b'r tequila vodka')))
