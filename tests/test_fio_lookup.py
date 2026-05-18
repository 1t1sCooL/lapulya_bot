"""
Тесты для modules/fio_lookup.py.
Запуск: pytest tests/test_fio_lookup.py -v
"""
import pytest
from unittest.mock import AsyncMock, patch

from modules.fio_lookup import transliterate_name, generate_username_variants, fio_search


class TestTransliterateName:
    def test_basic(self):
        assert transliterate_name("Иванов") == "ivanov"

    def test_yo(self):
        # "Ё" → "yo", поэтому Ёжиков → yozhikov (ГОСТ-транслит)
        assert transliterate_name("Ёжиков") == "yozhikov"

    def test_mixed_case(self):
        # Функция приводит к нижнему регистру
        result = transliterate_name("ИВАНОВ")
        assert result == "ivanov"

    def test_soft_hard_sign_removed(self):
        assert transliterate_name("Объект") == "obekt"
        assert transliterate_name("Семья") == "semya"

    def test_latin_passthrough(self):
        # Латиница должна пройти без изменений
        assert transliterate_name("Ivan") == "ivan"


class TestGenerateUsernameVariants:
    def test_returns_list(self):
        result = generate_username_variants("Иван", "Иванов")
        assert isinstance(result, list)

    def test_minimum_variants(self):
        result = generate_username_variants("Иван", "Иванов")
        assert len(result) >= 4

    def test_all_strings(self):
        result = generate_username_variants("Иван", "Иванов")
        assert all(isinstance(v, str) for v in result)

    def test_no_duplicates(self):
        result = generate_username_variants("Иван", "Иванов")
        assert len(result) == len(set(result))

    def test_lowercase(self):
        result = generate_username_variants("Иван", "Иванов")
        assert all(v == v.lower() for v in result)

    def test_no_empty_strings(self):
        result = generate_username_variants("Иван", "Иванов")
        assert all(v for v in result)

    def test_with_middle_name(self):
        result = generate_username_variants("Иван", "Иванов", "Иванович")
        # Должен быть вариант с инициалами: ivanov_ii
        assert any("ii" in v for v in result)

    def test_known_variants_present(self):
        result = generate_username_variants("Иван", "Иванов")
        # Хотя бы один вариант содержит "ivanov"
        assert any("ivanov" in v for v in result)


class TestFioSearch:
    @pytest.mark.asyncio
    async def test_returns_all_keys(self):
        """fio_search возвращает dict со всеми ожидаемыми ключами."""
        mock_result = {"found": 0, "results": []}
        mock_error = {"error": "no key"}

        with (
            patch("modules.fio_lookup.leakcheck_search", new_callable=AsyncMock, return_value=mock_result),
            patch("modules.fio_lookup.dehashed_search", new_callable=AsyncMock, return_value=mock_result),
            patch("modules.fio_lookup.intelx_search", new_callable=AsyncMock, return_value=mock_result),
            patch("modules.fio_lookup.vk_user_search", new_callable=AsyncMock, return_value=mock_result),
            patch("modules.fio_lookup.hh_resume_search", new_callable=AsyncMock, return_value=mock_result),
        ):
            result = await fio_search("Иван", "Иванов", leakcheck_key="key")

        assert "breach_lc" in result
        assert "breach_dh" in result
        assert "breach_ix" in result
        assert "vk" in result
        assert "hh" in result
        assert "username_variants" in result

    @pytest.mark.asyncio
    async def test_username_variants_not_empty(self):
        """username_variants всегда генерируются, даже если все источники ошиблись."""
        with (
            patch("modules.fio_lookup.leakcheck_search", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch("modules.fio_lookup.dehashed_search", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch("modules.fio_lookup.intelx_search", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch("modules.fio_lookup.vk_user_search", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch("modules.fio_lookup.hh_resume_search", new_callable=AsyncMock, side_effect=Exception("fail")),
        ):
            result = await fio_search("Иван", "Иванов")

        assert len(result["username_variants"]) >= 4

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_break(self):
        """Если один источник падает, остальные результаты всё равно возвращаются."""
        good_result = {"found": 3, "results": [{"email": "test@test.com"}]}

        with (
            patch("modules.fio_lookup.leakcheck_search", new_callable=AsyncMock, side_effect=Exception("boom")),
            patch("modules.fio_lookup.dehashed_search", new_callable=AsyncMock, return_value=good_result),
            patch("modules.fio_lookup.intelx_search", new_callable=AsyncMock, return_value=good_result),
            patch("modules.fio_lookup.vk_user_search", new_callable=AsyncMock, return_value=good_result),
            patch("modules.fio_lookup.hh_resume_search", new_callable=AsyncMock, return_value=good_result),
        ):
            result = await fio_search("Иван", "Иванов", leakcheck_key="k")

        # leakcheck вернул ошибку
        assert "error" in result["breach_lc"]
        # остальные работают
        assert result["breach_dh"]["found"] == 3
        assert result["vk"]["found"] == 3
        assert result["hh"]["found"] == 3

    @pytest.mark.asyncio
    async def test_all_sources_called(self):
        """fio_search вызывает все 5 источников."""
        mock_lc = AsyncMock(return_value={"found": 0, "results": []})
        mock_dh = AsyncMock(return_value={"found": 0, "results": []})
        mock_ix = AsyncMock(return_value={"found": 0, "results": []})
        mock_vk = AsyncMock(return_value={"found": 0, "results": []})
        mock_hh = AsyncMock(return_value={"found": 0, "results": []})

        with (
            patch("modules.fio_lookup.leakcheck_search", mock_lc),
            patch("modules.fio_lookup.dehashed_search", mock_dh),
            patch("modules.fio_lookup.intelx_search", mock_ix),
            patch("modules.fio_lookup.vk_user_search", mock_vk),
            patch("modules.fio_lookup.hh_resume_search", mock_hh),
        ):
            await fio_search("Иван", "Иванов", leakcheck_key="k", dehashed_key="k2")

        mock_lc.assert_called_once()
        mock_dh.assert_called_once()
        mock_ix.assert_called_once()
        mock_vk.assert_called_once()
        mock_hh.assert_called_once()
