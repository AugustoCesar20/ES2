from unittest.mock import patch
from toolkit_cli import Timer

@patch("time.sleep", return_value=None)
def test_timer_countdown_termina_rapido(mock_sleep):
    with patch("time.time", side_effect=[1000.0, 1000.0, 1002.0]):
        Timer.countdown(1) 
    assert mock_sleep.called
