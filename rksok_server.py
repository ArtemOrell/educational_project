import asyncio
import logging.config
import re
import sys
from pathlib import Path
from typing import Union, Iterable

import aiofiles.os
import yaml

from custom_enums import ValidationWords, RequestVerbs, ResponseWords
from custom_exceptions import NotSpecifiedIPOrPortError, CanNotParseRequestError, CanNotParseResponseError, \
    CannotFetchDataFromValidationServer

# read logger config from logger_config.yaml
with open('logger_config.yml', 'r') as file:
    logger_config = yaml.safe_load(file.read())
    logging.config.dictConfig(logger_config)

logger = logging.getLogger('RKSOK_Logger')

PROTOCOL = 'РКСОК/1.0'
ENCODING = 'UTF-8'
ALLOWED_NAME_LENGTH = 30

CustomRequestType = RequestVerbs


def get_server_and_port() -> tuple[str, int]:
    """Returns Server and Port from command-line arguments."""
    try:
        return sys.argv[1], int(sys.argv[2])
    except (IndexError, ValueError):
        raise NotSpecifiedIPOrPortError()


class RKSOKServer:
    def __init__(self, validation_server: str, port: int):
        self.validation_server = validation_server
        self.port = port
        self.path_to_phonebook = Path('./rksok_phonebook').resolve()
        self.name: Union[str, None]
        self.request_type: CustomRequestType
        self.phones: Iterable[str]
        self.crud_dict = {
            RequestVerbs.WRITE: self._write_phones,
            RequestVerbs.GET: self._read_phones,
            RequestVerbs.DELETE: self._delete_file
        }

    @staticmethod
    async def _receiving_data(reader: asyncio.StreamReader) -> bytearray:
        """ Data receiving. """

        data = bytearray()
        while True:
            chunk = await reader.read(4096)
            data += chunk
            if chunk == b'' or chunk.decode().endswith('\r\n\r\n'):
                break
        return data

    @staticmethod
    async def _is_path_exists(path: Union[str, Path]):
        """ Function checks if the file with a particular name exists"""

        try:
            await aiofiles.os.stat(str(path))
            return True
        except (OSError, ValueError):
            return False

    async def _write_phones(self) -> str:
        """ Function writes phones into file and generates the response to a client. """

        if not await self._is_path_exists(self.path_to_phonebook):
            logger.debug(f'Create folder{self.path_to_phonebook}...')
            await aiofiles.os.mkdir(self.path_to_phonebook)
        async with aiofiles.open(f'{self.path_to_phonebook}/{self.name}', mode='w', encoding='UTF-8') as f:
            logger.debug(f'Write phones to a file:{self.path_to_phonebook}/{self.name}')
            await f.write('\r\n'.join(self.phones))
        response_to_client = f'{ResponseWords.OK.value} {PROTOCOL}\r\n\r\n'
        return response_to_client

    async def _read_phones(self) -> str:
        """ Function reads phones from a file and generates the response to a client . """

        if not await self._is_path_exists(f'{self.path_to_phonebook}/{self.name}'):
            logger.debug(f'File with name: {self.name} does not exist')
            response_to_client = f'{ResponseWords.NOT_FOUND.value} {PROTOCOL}\r\n\r\n'
        else:
            async with aiofiles.open(f'{self.path_to_phonebook}/{self.name}', mode='r', encoding='UTF-8') as f:
                logger.debug(f'Read phones from: {self.path_to_phonebook}/{self.name}')
                data = '\r\n'.join(str(_).strip() for _ in await f.readlines())
                response_to_client = f'{ResponseWords.OK.value} {PROTOCOL}\r\n{data}\r\n\r\n'
        return response_to_client

    async def _delete_file(self) -> str:
        """ Function delete file if exists and generates the response to a client """

        if not await self._is_path_exists(f'{self.path_to_phonebook}/{self.name}'):
            logger.debug(f'File with name: {self.name} does not exist')
            response_to_client = f'{ResponseWords.NOT_FOUND.value} {PROTOCOL}\r\n\r\n'
        else:
            logger.debug(f'Remove file: {self.path_to_phonebook}/{self.name}')
            await aiofiles.os.remove(f'{self.path_to_phonebook}/{self.name}')
            response_to_client = f'{ResponseWords.OK.value} {PROTOCOL}\r\n\r\n'
        return response_to_client

    def _check_phones_in_request(self, request_payload: list) -> bool:
        """ Checks if request body  contains at least one phone.
        Phone can not be an empty string or space.
        Phone can not start or ends with space."""

        logger.debug(f'Phones in request: {request_payload}')
        self.phones = request_payload
        return self.phones == [_.strip() for _ in request_payload if _.strip()]

    def _check_request_body(self, raw_request: str) -> Union[bool, CanNotParseRequestError]:
        """ Check if the request body ends with proper sequence and doesn't contain escape sequences e.g. '\r', '\n'
        and name length doesn't exceed 30 symbols. Also name can not be an empty string or space. """

        request_payload = [_ for _ in raw_request.split('\r\n') if _]
        logger.debug(f'Request payload is: {request_payload}')
        elements = ('\r', '\n')
        if not request_payload[0].endswith(f' {PROTOCOL}') or any(el in _ for _ in request_payload for el in elements):
            logger.debug('Request body contains "\\r" or "\\n" or ends with wrong protocol')
            return False
        pattern = re.compile(r'\s+(([^\s]+\s+)+)(?=РКСОК/1\.0)')
        try:
            name = re.search(pattern, request_payload[0])
            assert name is not None
            self.name = name.group()[1: -1]
            if not (len(self.name) <= ALLOWED_NAME_LENGTH and self._check_phones_in_request(request_payload[1:])):
                logger.debug(
                    'Name exceeds allowed length or request does not contain any phone numbers '
                    'or space in the wrong place of the phone number.')
                return False
            return True

        # if name is a sequence of spaces raise AttributeError exception
        except AttributeError as e:
            logger.debug(e, exc_info=True)
            return False

    async def _is_valid_request(self, raw_request: str) -> Union[bool, CanNotParseRequestError]:
        """ Function check if the request starts with the proper verb ends with the proper sequence of characters
        and contains only one '\r\n\r\n' sequence. """
        logger.debug(f'Received raw_request: {raw_request!r}')
        for request_verb in RequestVerbs:
            if raw_request.startswith(f'{request_verb.value} '):
                self.request_type = request_verb
                break
        else:
            try:
                wrong_verb = raw_request.split()[0]
                logger.debug(
                    f'Wrong validation verb: {wrong_verb}. '
                    f'Message must starts with one of the following verbs:  ОТДОВАЙ, ЗОПИШИ, УДОЛИ')
                raise CanNotParseRequestError()
            except IndexError:
                raise CanNotParseRequestError()

        if (raw_request.endswith(f' {PROTOCOL}\r\n\r\n') or raw_request.endswith(
                '\r\n\r\n')) and not raw_request.endswith(' \r\n\r\n') \
                and raw_request.count('\r\n\r\n') == 1:
            if self._check_request_body(raw_request):
                assert self.name is not None
                self.name = self.name.strip()
                return True
            logger.debug('Either wrong escape sequence or protocol')
            raise CanNotParseRequestError
        logger.debug('Either wrong escape sequence or protocol')
        raise CanNotParseRequestError

    @staticmethod
    async def _write_and_close(response: str, writer: asyncio.StreamWriter) -> None:
        """ Write response to a buffer and close connection."""

        logger.debug(f'Response to a client: {response!r}')
        writer.write(response.encode(ENCODING))
        await writer.drain()
        writer.close()

    @staticmethod
    async def _response_if_exception(writer: asyncio.StreamWriter) -> None:
        """ Response to a client either if incorrect request or cannot fetch response from validation server or can not
        fetch request from a client. """
        response = f'{ResponseWords.INCORRECT.value} {PROTOCOL}\r\n\r\n'
        await RKSOKServer._write_and_close(response, writer)

    async def _tcp_echo_client(self, message_to_server: str) -> bytes:
        """Function sends correct request to the validation server to check if the request is approved"""
        try:
            reader, writer = await asyncio.open_connection(self.validation_server, self.port, limit=2 ** 22)
            message = f'{ValidationWords.IS_ALLOWED.value} {PROTOCOL}\r\n{message_to_server}'
            logger.debug(f'Request to validation server: {message!r}')
            writer.write(message.encode(ENCODING))
            data = await asyncio.wait_for(self._receiving_data(reader), timeout=5)
            logger.debug(f'Response from validation server: {data.decode(ENCODING)!r}')
            writer.close()
            return data
        except asyncio.exceptions.TimeoutError:
            logger.error('Время ожидания от сервера проверки превышено!!! asyncio.exceptions.TimeoutError')
            raise CannotFetchDataFromValidationServer
        except ConnectionRefusedError:
            logger.debug(
                f'Не могу подключиться к указанному домену или порту сервера проверки: domain:{self.validation_server}'
                f' port:{self.port}',
                exc_info=True)
            raise CannotFetchDataFromValidationServer

    async def handle_echo(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """ Handle request from a client and send the response. """

        try:
            logger.info('Start processing new request from a client')
            data = await asyncio.wait_for(self._receiving_data(reader), timeout=5)
            message = f'{data.decode(ENCODING)}'
            logger.debug(f'Start checking request from a client: {message!r}')
            await self._is_valid_request(message)
            server_response_coro = await self._tcp_echo_client(message)
            server_response = server_response_coro.decode(ENCODING)
            for validation_verb in ValidationWords:
                if server_response.startswith(f'{validation_verb.value} '):
                    break
            else:
                logger.debug('Response from validation server must starts with: МОЖНА, НИЛЬЗЯ')
                raise CanNotParseResponseError()
            if not server_response.startswith(f'{ValidationWords.ALLOWED.value} '):
                await self._write_and_close(server_response, writer)
            else:
                response = self.crud_dict.get(self.request_type)
                assert response is not None
                response_ = await response()
                await self._write_and_close(response_, writer)
        except (asyncio.exceptions.TimeoutError, CanNotParseRequestError, CanNotParseResponseError,
                CannotFetchDataFromValidationServer):
            exc_type = sys.exc_info()[0]
            logger.debug(exc_type)
            logger.debug(f'{exc_type}.  Client sends either empty string or spaces sequence or message does not ends '
                         f'with \\r\\n\\r\\n sequence')
            await self._response_if_exception(writer)


async def _main():
    """ Getting and processing data from a client. """
    try:
        validation_server, port = get_server_and_port()

        rksok_instance = RKSOKServer(validation_server, port)
        server = await asyncio.start_server(rksok_instance.handle_echo, '0.0.0.0', 8888, limit=2 ** 22)

        addr = server.sockets[0].getsockname()
        logger.debug(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    except NotSpecifiedIPOrPortError:
        print("Упс! Меня запускать надо так:\n\n"
              "python3.9 rksok_server.py SERVER PORT\n\n"
              "где SERVER и PORT — это домен и порт сервера проверки, "
              "к которому мы будем подключаться. Пример:\n\n"
              "python3.9 rksok_server.py vragi-vezde.to.digital 51624\n", file=sys.stderr)
        logger.critical('Not specified port or server', exc_info=True)
        exit(1)


if __name__ == '__main__':
    """ An entry point. """
    asyncio.run(_main())
